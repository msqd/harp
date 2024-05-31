import asyncio
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Iterable, List, Optional, TypedDict, override

from sqlalchemy import bindparam, case, delete, func, literal, literal_column, select, text, update
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker, create_async_engine
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
from harp.utils.tpdex import tpdex
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
}


def _filter_query(query, name, values):
    if values and values != "*":
        query = query.filter(
            getattr(
                Transaction,
                _FILTER_COLUMN_NAMES.get(name, name),
            ).in_(values)
        )
    return query


def _filter_query_for_user_flags(query, values, /, *, user_id):
    if values and values != "*":
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
    query = query.join(Message)
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
        self.engine = create_async_engine(self.settings.url, echo=self.settings.echo)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

        # TODO is this the right place ? (maybe it is, but maybe it causes tight coupling to the ed which may be not
        #      right, especially if we want to be able to use the storage out of the special context of harp proxy)
        dispatcher.add_listener(EVENT_CORE_STARTED, self._on_startup_actions, priority=-20)
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self._on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self._on_transaction_message)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self._on_transaction_ended)

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

    @asynccontextmanager
    async def begin(self):
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    async def initialize(self, /, *, force_reset=False):
        """Create the database tables. May drop them first if configured to do so."""
        async with self.engine.begin() as conn:
            if force_reset or self.settings.drop_tables:
                await conn.run_sync(self.metadata.drop_all)

        async with self.engine.begin() as conn:
            await self.install_pg_trgm_extension(conn)

        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)

        async with self.engine.begin() as conn:
            await self.create_full_text_indexes(conn)

        await self.create_users(["anonymous"])
        self._is_ready.set()

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
    async def get_transaction(
        self,
        id: str,
        /,
        *,
        username: str,
    ) -> Optional[TransactionModel]:
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
            func.avg(Transaction.apdex),
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
                    "meanApdex": row[4],
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

        def create_blob_storage_task(blob):
            async def store_blob():
                async with self.begin() as session:
                    db_blob = Blob()
                    db_blob.id = blob.id
                    db_blob.content_type = blob.content_type
                    db_blob.data = blob.data
                    session.add(db_blob)

            return store_blob

        await self.worker.push(create_blob_storage_task(headers_blob), ignore_errors=True)
        await self.worker.push(create_blob_storage_task(content_blob), ignore_errors=True)

        async def store_message():
            async with self.begin() as session:
                session.add(
                    Message.from_models(event.transaction, event.message, headers_blob, content_blob),
                )

        await self.worker.push(store_message)

    async def _on_transaction_ended(self, event: TransactionEvent):
        async def finalize_transaction():
            async with self.begin() as session:
                await session.execute(
                    update(Transaction)
                    .where(Transaction.id == event.transaction.id)
                    .values(
                        finished_at=event.transaction.finished_at.astimezone(UTC),
                        elapsed=event.transaction.elapsed,
                        apdex=tpdex(event.transaction.elapsed),
                        x_status_class=event.transaction.extras.get("status_class"),
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

    async def install_pg_trgm_extension(self, conn: AsyncConnection):
        # Check the type of the current database
        if conn.engine.dialect.name == "postgresql":
            # Install the pg_trgm extension if possible
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            except DatabaseError as e:
                logger.error(f"Failed to install pg_trgm extension: {e}")

    async def create_full_text_indexes(self, conn: AsyncConnection):
        # Check the type of the current database
        if conn.engine.dialect.name == "mysql":
            # Create the full text index for transactions.endpoint
            try:
                await conn.execute(
                    text(f"CREATE FULLTEXT INDEX endpoint_ft_index ON {Transaction.__tablename__} (endpoint);")
                )
                # Create the full text index for messages.summary
                await conn.execute(
                    text(f"CREATE FULLTEXT INDEX summary_ft_index ON {Message.__tablename__} (summary);")
                )
            except OperationalError as e:
                # check for duplicate key error
                if e.orig and e.orig.args[0] == 1061:
                    pass
                else:
                    raise e
