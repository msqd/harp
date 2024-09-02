import asyncio
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from operator import itemgetter
from typing import Iterable, Optional, override

from sqlalchemy import and_, bindparam, case, delete, func, literal, literal_column, null, or_, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.sql.functions import count

from harp import get_logger
from harp.models import Results, Transaction
from harp.settings import PAGE_SIZE
from harp.utils.background import AsyncWorkerQueue
from harp.utils.dates import ensure_datetime
from harp_apps.storage.constants import TimeBucket
from harp_apps.storage.models import FLAGS_BY_NAME, Base, BlobsRepository, FlagsRepository
from harp_apps.storage.models import Message as SqlMessage
from harp_apps.storage.models import (
    MessagesRepository,
    MetricsRepository,
    MetricValuesRepository,
    TagsRepository,
    TagValuesRepository,
)
from harp_apps.storage.models import Transaction as SqlTransaction
from harp_apps.storage.models import TransactionsRepository
from harp_apps.storage.models import User as SqlUser
from harp_apps.storage.models import UserFlag as SqlUserFlag
from harp_apps.storage.models import UsersRepository
from harp_apps.storage.settings import StorageSettings
from harp_apps.storage.types import IBlobStorage, IStorage, TransactionsGroupedByTimeBucket
from harp_apps.storage.utils.dates import TruncDatetime

logger = get_logger(__name__)

_FILTER_COLUMN_NAMES = {
    "method": "x_method",
    "status": "x_status_class",
    "tpdex": "tpdex",
}


def _numerical_filter_query(query, name: str, values: dict[str, float]):
    if values:
        column_name = _FILTER_COLUMN_NAMES.get(name, name)
        column = getattr(SqlTransaction, column_name)

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
                SqlTransaction,
                _FILTER_COLUMN_NAMES.get(name, name),
            ).in_(values)
        )
    return query


def _filter_query_for_user_flags(query, values, /, *, user_id):
    if values:
        if "NULL" in values:
            query = query.outerjoin(SqlUserFlag).filter(
                or_(
                    and_(
                        SqlUserFlag.user_id == user_id,
                        SqlUserFlag.type.in_(
                            list(
                                map(FLAGS_BY_NAME.get, values),
                            )
                        ),
                    ),
                    or_(SqlUserFlag.user_id != user_id, (SqlUserFlag.type.is_(null()))),
                )
            )
        else:
            query = query.join(SqlUserFlag).filter(
                SqlUserFlag.user_id == user_id,
                SqlUserFlag.type.in_(
                    list(
                        map(FLAGS_BY_NAME.get, values),
                    )
                ),
            )
    return query


def _filter_transactions_based_on_text(query, search_text: str, dialect_name: str):
    # Escape special characters in search_text
    search_text = re.sub(r"([-\*\(\)~\"@<>\^+]+)", r"", search_text)
    query = query.join(SqlMessage, isouter=True)
    # check dialect and use appropriate full text search
    if dialect_name == "mysql":
        return query.filter(
            text(
                f"MATCH ({SqlTransaction.__tablename__}.endpoint) "
                f"AGAINST (:search_text IN BOOLEAN MODE) OR "
                f"MATCH ({SqlMessage.__tablename__}.summary) "
                f"AGAINST (:search_text IN BOOLEAN MODE)",
            ).bindparams(bindparam("search_text", literal_column(f"'{search_text}*'")))
        )

    return query.filter(
        (SqlTransaction.endpoint.ilike(bindparam("search_text", f"%{search_text}%")))
        | SqlMessage.summary.ilike(bindparam("search_text", f"%{search_text}%"))
    )


class SqlStorage(IStorage):
    """
    Storage implementation using SQLAlchemy (async).

    Currently supported/tested database drivers:

    - asyncpg (postgresql+asyncpg://...)
    - aiomysql (mysql+aiomysql://...)
    - asyncmy (mysql+asyncmy://...)

    And also, for development/testing purposes:

    - aiosqlite (sqlite+aiosqlite://...)

    Other async postgresql drivers may work, but as they're not included in the test suite, you may have surprises.
    Contributions welcome.

    """

    engine: AsyncEngine
    """Reference to the sqlalchemy async engine, which is a gateway to the database connectivity, able to provide a
    connection used to execute queries."""

    def __init__(self, engine: AsyncEngine, blob_storage: IBlobStorage, settings: StorageSettings):
        # XXX lokks like settings are not used anymore, except to know if we should run migrations or not
        self._should_migrate = settings.migrate

        self.metadata = Base.metadata

        self.blob_storage = blob_storage

        self.engine = engine
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

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

        logger.info(f"🛢 {type(self).__name__} url={self.engine.url}")

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
                        statement.compile(
                            session.sync_session.bind,
                            compile_kwargs={"literal_binds": True},
                        )
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
                                    map(
                                        _get0,
                                        original_execute(text("EXPLAIN ANALYZE " + sql_query)).fetchall(),
                                    )
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
        await self.create_users(["anonymous"])
        self._is_ready.set()

    async def finalize(self):
        await self.worker.close()
        await self.engine.dispose()

    @property
    def worker(self):
        if not self._worker:
            self._worker = AsyncWorkerQueue()
        return self._worker

    @override
    async def get_facet_meta(self, name):
        if name == "endpoint":
            # get transaction count grouped by endpoint
            async with self.begin() as session:
                query = select(SqlTransaction.endpoint, func.count()).group_by(SqlTransaction.endpoint)
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

        query = query.order_by(SqlTransaction.started_at.desc())

        # apply cursor (before count)
        if page and cursor:
            query = query.filter(SqlTransaction.id <= cursor)

        async with self.begin() as session:
            # count items from query
            result.meta["total"] = await session.scalar(
                query.with_only_columns(func.count(SqlTransaction.id)).order_by(None)
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
    async def get_transaction(self, id: str, /, *, username: str) -> Optional[Transaction]:
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
        *,
        endpoint: Optional[str] = None,
        time_bucket: str = TimeBucket.DAY.value,
        start_datetime: Optional[datetime] = None,
    ) -> list[TransactionsGroupedByTimeBucket]:
        if time_bucket not in [e.value for e in TimeBucket]:
            raise ValueError(
                f"Invalid time bucket: {time_bucket}. Must be one of {', '.join([e.value for e in TimeBucket])}."
            )

        s_date = TruncDatetime(literal(time_bucket), SqlTransaction.started_at).label("tb")
        query = select(
            s_date,
            func.count(),
            func.sum(case((SqlTransaction.x_status_class.in_(("5xx", "ERR")), 1), else_=0)),
            func.sum(
                case(
                    (
                        and_(
                            SqlTransaction.x_cached is not None,
                            SqlTransaction.x_cached != "",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.avg(SqlTransaction.elapsed),
            func.avg(SqlTransaction.tpdex),
        )

        if endpoint:
            query = query.where(SqlTransaction.endpoint == endpoint)

        if start_datetime:
            query = query.where(SqlTransaction.started_at >= start_datetime.astimezone(UTC))

        query = query.group_by(s_date).order_by(s_date.asc())
        async with self.begin() as session:
            result = await session.execute(query)
            return [
                TransactionsGroupedByTimeBucket(
                    datetime=ensure_datetime(row[0], UTC),
                    count=row[1],
                    errors=int(row[2]),
                    cached=int(row[3]),
                    meanDuration=row[4] if row[4] else 0,
                    meanTpdex=row[5],
                )
                for row in result.fetchall()
            ]

    async def get_usage(self):
        async with self.begin() as session:
            query = select(count(SqlTransaction.id)).where(
                SqlTransaction.started_at > (datetime.now(UTC) - timedelta(hours=24))
            )
            return (await session.execute(query)).scalar_one_or_none()

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
                    SqlUserFlag(
                        transaction_id=transaction.id,
                        user_id=user.id,
                        type=flag,
                    )
                )
            else:
                await session.execute(
                    delete(SqlUserFlag).where(
                        SqlUserFlag.transaction_id == transaction.id,
                        SqlUserFlag.user_id == user.id,
                    )
                )

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
                result = await session.execute(select(SqlUser).where(SqlUser.username == username))
                existing_user = result.scalar_one_or_none()

                # If the username does not exist, create a new user
                if existing_user is None:
                    user = SqlUser()
                    user.username = username
                    session.add(user)
