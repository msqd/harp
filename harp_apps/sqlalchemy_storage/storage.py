import asyncio
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from functools import partial
from operator import itemgetter
from typing import Iterable, List, Optional, TypedDict, override

from sqlalchemy import and_, bindparam, case, delete, func, literal, literal_column, null, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.sql.functions import count
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.asgi.events import EVENT_CORE_STARTED, MessageEvent, TransactionEvent
from harp.http import get_serializer_for
from harp.models import Blob as BlobModel
from harp.models.base import Results
from harp.models.transactions import Transaction as TransactionModel
from harp.settings import PAGE_SIZE
from harp.typing.storage import Storage
from harp.utils.background import AsyncWorkerQueue
from harp.utils.dates import ensure_datetime
from harp_apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED

from .constants import TimeBucket
from .models import (
    FLAGS_BY_NAME,
    Base,
    Blob,
    BlobsRepository,
    FlagsRepository,
    Message,
    MessagesRepository,
    MetricsRepository,
    MetricValuesRepository,
    TagsRepository,
    TagValuesRepository,
    Transaction,
    TransactionsRepository,
    User,
    UserFlag,
    UsersRepository,
)
from .settings import SqlAlchemyStorageSettings
from .utils.dates import TruncDatetime


class TransactionsGroupedByTimeBucket(TypedDict):
    datetime: datetime | None
    count: int
    errors: int
    meanDuration: float


logger = get_logger(__name__)

_FILTER_COLUMN_NAMES = {
    "method": "x_method",
    "status": "x_status_class",
    "tpdex": "tpdex",
}


def _numerical_filter_query(query, name: str, values: dict[str, float]):
    if values:
        column_name = _FILTER_COLUMN_NAMES.get(name, name)
        column = getattr(Transaction, column_name)

        min_val = values.get("min")
        max_val = values.get("max")

        if min_val is not None and max_val is not None:
            query = query.filter(column.between(min_val, max_val))
        elif min_val is not None:
            query = query.filter(column >= min_val)
        elif max_val is not None:
            query = query.filter(column <= max_val)

    return query


def _filter_query(query, name, values):
    if values:
        query = query.filter(
            getattr(
                Transaction,
                _FILTER_COLUMN_NAMES.get(name, name),
            ).in_(values)
        )
    return query


def _filter_query_for_user_flags(query, values, /, *, user_id):
    if values:
        if "NULL" in values:
            query = query.outerjoin(UserFlag).filter(
                or_(
                    and_(
                        UserFlag.user_id == user_id,
                        UserFlag.type.in_(
                            list(
                                map(FLAGS_BY_NAME.get, values),
                            )
                        ),
                    ),
                    or_(UserFlag.user_id != user_id, (UserFlag.type.is_(null()))),
                )
            )
        else:
            query = query.join(UserFlag).filter(
                UserFlag.user_id == user_id,
                UserFlag.type.in_(
                    list(
                        map(FLAGS_BY_NAME.get, values),
                    )
                ),
            )
    return query


def _filter_transactions_based_on_text(query, search_text: str, dialect_name: str):
    # Escape special characters in search_text
    search_text = re.sub(r"([-\*\(\)~\"@<>\^+]+)", r"", search_text)
    query = query.join(Message, isouter=True)
    # check dialect and use appropriate full text search
    if dialect_name == "mysql":
        return query.filter(
            text(
                f"MATCH ({Transaction.__tablename__}.endpoint) "
                f"AGAINST (:search_text IN BOOLEAN MODE) OR "
                f"MATCH ({Message.__tablename__}.summary) "
                f"AGAINST (:search_text IN BOOLEAN MODE)",
            ).bindparams(bindparam("search_text", literal_column(f"'{search_text}*'")))
        )

    return query.filter(
        (Transaction.endpoint.ilike(bindparam("search_text", f"%{search_text}%")))
        | Message.summary.ilike(bindparam("search_text", f"%{search_text}%"))
    )


class SqlAlchemyStorage(Storage):
    """
    Storage implementation using SQL Alchemy Core, with async drivers.

    Currently supported/tested database drivers:

    - aiosqlite (sqlite+aiosqlite://...)

    """

    engine: AsyncEngine
    """Reference to the sqlalchemy async engine, which is a gateway to the database connectivity, able to provide a
    connection used to execute queries."""

    def __init__(self, dispatcher: IAsyncEventDispatcher, settings: SqlAlchemyStorageSettings):
        self.settings = settings
        self.metadata = Base.metadata

        self.engine = create_async_engine(self.settings.url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

        # TODO is this the right place ? (maybe it is, but maybe it causes tight coupling to the ed which may be not
        #      right, especially if we want to be able to use the storage out of the special context of harp proxy)
        dispatcher.add_listener(EVENT_CORE_STARTED, self._on_startup_actions, priority=-20)
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self._on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self._on_transaction_message)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self._on_transaction_ended)
        self._dispatcher = dispatcher

        self._is_ready = asyncio.Event()
        self._worker = None

        self.blobs = BlobsRepository(self.session_factory)
        self.messages = MessagesRepository(self.session_factory)
        self.tags = TagsRepository(self.session_factory)
        self.tag_values = TagValuesRepository(self.session_factory)
        self.transactions = TransactionsRepository(self.session_factory, tags=self.tags, tag_values=self.tag_values)
        self.users = UsersRepository(self.session_factory)
        self.metrics = MetricsRepository(self.session_factory)
        self.metric_values = MetricValuesRepository(self.session_factory)
        self.flags = FlagsRepository(self.session_factory)

        self._debug = False

    @asynccontextmanager
    async def begin(self):
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    def install_debugging_instrumentation(self, *, echo=False):
        self._debug = True
        self._original_session_factory = self.session_factory
        self._debug_index = 1
        self.sql_queries = []

        if echo:
            from rich.console import Console
            from rich.syntax import Syntax

            _console = Console(force_terminal=True, width=180)

        @asynccontextmanager
        async def _session_factory():
            async with self._original_session_factory() as session:
                original_execute = session.sync_session._execute_internal

                def _instrumented_execute(statement, *args, **kwargs):
                    sql_query = str(
                        statement.compile(session.sync_session.bind, compile_kwargs={"literal_binds": True})
                    )
                    self.sql_queries.append(sql_query)

                    final_result = original_execute(statement, *args, **kwargs)

                    if echo:
                        _console.print(f"🛢 SQL QUERY (#{self._debug_index})", style="bold")
                        _console.print(
                            Syntax(
                                sql_query,
                                "sql",
                                word_wrap=True,
                                theme="vs",
                            )
                        )

                    if echo and self.engine.dialect.name == "postgresql":
                        _get0 = itemgetter(0)
                        _console.print(f"🛢 EXPLAIN ANALYZE (#{self._debug_index})", style="bold")
                        _console.print(
                            Syntax(
                                "\n".join(
                                    map(_get0, original_execute(text("EXPLAIN ANALYZE " + sql_query)).fetchall())
                                ),
                                "sql",
                                word_wrap=True,
                                theme="vs",
                            )
                        )

                    self._debug_index += 1
                    return final_result

                session.sync_session._execute_internal = _instrumented_execute
                try:
                    yield session
                finally:
                    session.sync_session._execute_internal = original_execute

        self.session_factory = _session_factory

    async def initialize(self):
        """Initialize database."""
        if self.settings.migrate:
            await self._run_migrations()
        await self.create_users(["anonymous"])
        self._is_ready.set()

    async def _run_migrations(self):
        """Convenience helper to run the migrations. This behaviour can be disabled by setting migrate=false in the
        storage settings."""
        from alembic import command

        from harp_apps.sqlalchemy_storage.utils.migrations import create_alembic_config

        from .utils.migrations import do_migrate

        alembic_cfg = create_alembic_config(self.engine.url.render_as_string(hide_password=False))

        migrator = partial(command.upgrade, alembic_cfg, "head")

        await do_migrate(self.engine, migrator=migrator)

    @property
    def worker(self):
        if not self._worker:
            self._worker = AsyncWorkerQueue()
        return self._worker

    async def wait_for_background_tasks_to_be_processed(self):
        if self._worker:
            await self._worker.wait_until_empty()

    @override
    async def get_facet_meta(self, name):
        if name == "endpoint":
            # get transaction count grouped by endpoint
            async with self.begin() as session:
                query = select(Transaction.endpoint, func.count()).group_by(Transaction.endpoint)
                result = await session.execute(query)
                return {row[0]: row[1] for row in result.fetchall()}

        raise NotImplementedError(f"Unknown facet: {name}")

    @override
    async def get_transaction_list(
        self,
        *,
        username: str,
        with_messages=False,
        filters=None,
        page: int = 1,
        cursor: str = "",
        text_search="",
    ):
        """
        Implements :meth:`Storage.find_transactions <harp.typing.storage.Storage.find_transactions>`.

        """

        user = await self.users.find_one_by_username(username)

        result = Results()
        query = self.transactions.select(
            with_messages=with_messages,
            with_user_flags=user.id if user else False,
            with_tags=True,
        )

        if filters:
            query = _filter_query(query, "endpoint", filters.get("endpoint", None))
            query = _filter_query(query, "method", filters.get("method", None))
            query = _filter_query(query, "status", filters.get("status", None))
            query = _filter_query_for_user_flags(query, filters.get("flag", None), user_id=user.id)
            query = _numerical_filter_query(query, "tpdex", filters.get("tpdex", None))

        if text_search:
            query = _filter_transactions_based_on_text(query, text_search, dialect_name=self.engine.dialect.name)

        query = query.order_by(Transaction.started_at.desc())

        # apply cursor (before count)
        if page and cursor:
            query = query.filter(Transaction.id <= cursor)

        async with self.begin() as session:
            # count items from query
            result.meta["total"] = await session.scalar(
                query.with_only_columns(func.count(Transaction.id)).order_by(None)
            )

        # apply limit/offset (after count)
        query = query.limit(PAGE_SIZE)
        if page:
            query = query.offset(max(0, (page - 1) * PAGE_SIZE))

        async with self.begin() as session:
            for transaction in (await session.scalars(query)).unique().all():
                result.append(transaction.to_model(with_user_flags=True))

        return result

    @override
    async def get_transaction(self, id: str, /, *, username: str) -> Optional[TransactionModel]:
        user = await self.users.find_one_by_username(username)

        return (
            await self.transactions.find_one_by_id(
                id,
                with_messages=True,
                with_user_flags=user.id if user else False,
                with_tags=True,
            )
        ).to_model(with_user_flags=True)

    @override
    async def transactions_grouped_by_time_bucket(
        self,
        endpoint: Optional[str] = None,
        time_bucket: str = TimeBucket.DAY.value,
        start_datetime: Optional[datetime] = None,
    ) -> List[TransactionsGroupedByTimeBucket]:
        if time_bucket not in [e.value for e in TimeBucket]:
            raise ValueError(
                f"Invalid time bucket: {time_bucket}. Must be one of {', '.join([e.value for e in TimeBucket])}."
            )

        s_date = TruncDatetime(literal(time_bucket), Transaction.started_at).label("tb")
        query = select(
            s_date,
            func.count(),
            func.sum(case((Transaction.x_status_class.in_(("5xx", "ERR")), 1), else_=0)),
            func.avg(Transaction.elapsed),
            func.avg(Transaction.tpdex),
        )

        if endpoint:
            query = query.where(Transaction.endpoint == endpoint)

        if start_datetime:
            query = query.where(Transaction.started_at >= start_datetime.astimezone(UTC))

        query = query.group_by(s_date).order_by(s_date.asc())
        async with self.begin() as session:
            result = await session.execute(query)
            return [
                {
                    "datetime": ensure_datetime(row[0], UTC),
                    "count": row[1],
                    "errors": int(row[2]),
                    "meanDuration": row[3] if row[3] else 0,
                    "meanTpdex": row[4],
                    # ! probably sqlite struggling with unfinished transactions
                }
                for row in result.fetchall()
            ]

    async def get_usage(self):
        async with self.begin() as session:
            query = select(count(Transaction.id)).where(
                Transaction.started_at > (datetime.now(UTC) - timedelta(hours=24))
            )
            return (await session.execute(query)).scalar_one_or_none()

    @override
    async def get_blob(self, blob_id):
        """
        Retrieve a blob from the database, using its hash.
        Returns None if not found.

        :param blob_id: sha1 hash of the blob
        :return: Blob or None
        """
        async with self.begin() as session:
            row = (
                await session.execute(
                    select(Blob).where(Blob.id == blob_id),
                )
            ).fetchone()

        if row:
            return BlobModel(id=blob_id, data=row[0].data, content_type=row[0].content_type)

    async def _on_startup_actions(self, TransactionEvent):
        """Event handler to create the database tables on startup. May drop them first if configured to do so."""
        await self.initialize()

    @override
    async def set_user_flag(self, *, transaction_id: str, username: str, flag: int, value=True):
        """Sets or unsets a user flag on a transaction."""
        async with self.begin() as session:
            user = await self.users.find_one_by_username(username)
            transaction = await self.transactions.find_one_by_id(transaction_id)

            if value:
                session.add(
                    UserFlag(
                        transaction_id=transaction.id,
                        user_id=user.id,
                        type=flag,
                    )
                )
            else:
                await session.execute(
                    delete(UserFlag).where(UserFlag.transaction_id == transaction.id, UserFlag.user_id == user.id)
                )

    async def _on_transaction_started(self, event: TransactionEvent):
        """Event handler to store the transaction in the database."""
        return await self.transactions.create(event.transaction)

    async def _on_transaction_message(self, event: MessageEvent):
        await event.message.join()
        serializer = get_serializer_for(event.message)

        # todo is the "__headers__" dunder content type any good idea ? maybe it's just a waste of bytes.
        headers_blob = BlobModel.from_data(serializer.headers, content_type="__headers__")
        content_blob = BlobModel.from_data(serializer.body, content_type=event.message.headers.get("content-type"))

        def create_store_blob_task(blob):
            async def store_blob_task():
                async with self.begin() as session:
                    if not (
                        await session.execute(select(select(Blob.id).where(Blob.id == blob.id).exists()))
                    ).scalar_one():
                        db_blob = Blob()
                        db_blob.id = blob.id
                        db_blob.content_type = blob.content_type
                        db_blob.data = blob.data
                        session.add(db_blob)

            return store_blob_task

        await self.worker.push(create_store_blob_task(headers_blob), ignore_errors=False)
        await self.worker.push(create_store_blob_task(content_blob), ignore_errors=True)

        async def store_message_task():
            async with self.begin() as session:
                session.add(
                    Message.from_models(event.transaction, event.message, headers_blob, content_blob),
                )

        await self.worker.push(store_message_task)

    async def _on_transaction_ended(self, event: TransactionEvent):
        async def finalize_transaction():
            async with self.begin() as session:
                await session.execute(
                    update(Transaction)
                    .where(Transaction.id == event.transaction.id)
                    .values(
                        finished_at=event.transaction.finished_at.astimezone(UTC),
                        elapsed=event.transaction.elapsed,
                        tpdex=event.transaction.tpdex,
                        x_status_class=event.transaction.extras.get("status_class"),
                        x_cached=event.transaction.extras.get("cached"),
                    )
                )

        await self.worker.push(finalize_transaction)

    async def ready(self):
        await self._is_ready.wait()

    @override
    async def create_users_once_ready(self, users: Iterable[str]):
        """Sets the list of users to be created once the database is ready."""

        async def defered_create_users():
            await self.ready()
            await self.create_users(users)

        await self.worker.push(defered_create_users)

    async def create_users(self, users: Iterable[str]):
        async with self.begin() as session:
            for username in users:
                # Check if the username already exists
                result = await session.execute(select(User).where(User.username == username))
                existing_user = result.scalar_one_or_none()

                # If the username does not exist, create a new user
                if existing_user is None:
                    user = User()
                    user.username = username
                    session.add(user)
