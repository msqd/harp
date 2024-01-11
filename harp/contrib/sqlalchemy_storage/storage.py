from datetime import UTC, date, datetime
from enum import Enum
from typing import Generic, List, Optional, TypedDict, TypeVar

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.contrib.sqlalchemy_storage.models import Base, Blobs, Messages, Transactions
from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.utils.dates import TruncDatetime
from harp.core.asgi.events import EVENT_CORE_STARTED, MessageEvent, TransactionEvent
from harp.core.models.blobs import Blob
from harp.core.models.transactions import Transaction
from harp.settings import PAGE_SIZE
from harp.utils.background import AsyncWorkerQueue
from harp.utils.dates import ensure_date, ensure_datetime


class TimeBucket(Enum):
    YEAR = "year"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"


class TransactionsGroupedByDate(TypedDict):
    date: date | datetime | None
    transactions: int
    errors: int
    meanDuration: float


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
                Transactions,
                _FILTER_COLUMN_NAMES.get(name, name),
            ).in_(values)
        )
    return query


T = TypeVar("T")


class Results(Generic[T]):
    def __init__(self):
        self.items: list[T] = []
        self.meta = {}

    def append(self, item: T):
        self.items.append(item)


class SqlAlchemyStorage:
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
        self.engine = create_async_engine(self.settings.url, echo=self.settings.echo)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.metadata = Base.metadata

        dispatcher.add_listener(EVENT_CORE_STARTED, self._on_startup_create_database, priority=-20)
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self._on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self._on_transaction_ended)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self._on_transaction_message)

        self._worker = None

    @property
    def worker(self):
        if not self._worker:
            self._worker = AsyncWorkerQueue()
        return self._worker

    async def get_facet_meta(self, name):
        if name == "endpoint":
            # get transaction count grouped by endpoint
            async with self.session() as session:
                query = select(Transactions.endpoint, func.count()).group_by(Transactions.endpoint)
                result = await session.execute(query)
                return {row[0]: row[1] for row in result.fetchall()}

        raise NotImplementedError(f"Unknown facet: {name}")

    async def find_transactions(
        self,
        *,
        with_messages=False,
        filters=None,
        page: int = 1,
        cursor: str = "",
    ) -> Results[Transaction]:
        """
        Implements :meth:`Storage.find_transactions <harp.protocols.storage.Storage.find_transactions>`.

        :param with_messages:
        :return:

        """
        result = Results()
        query = select(Transactions)
        if with_messages:
            query = query.options(joinedload(Transactions.messages))

        if filters:
            query = _filter_query(query, "endpoint", filters.get("endpoint", None))
            query = _filter_query(query, "method", filters.get("method", None))
            query = _filter_query(query, "status", filters.get("status", None))

        query = query.order_by(Transactions.started_at.desc())

        # apply cursor (before count)
        if page and cursor:
            query = query.filter(Transactions.id <= cursor)

        async with self.session() as session:
            # count items from query
            result.meta["total"] = await session.scalar(
                query.with_only_columns(func.count(Transactions.id)).order_by(None)
            )

        # apply limit/offset (after count)
        query = query.limit(PAGE_SIZE)
        if page:
            query = query.offset(max(0, (page - 1) * PAGE_SIZE))

        async with self.session() as session:
            for transaction in (await session.scalars(query)).unique().all():
                result.append(transaction.to_model())

        return result

    async def get_transaction(self, id: str) -> Optional[Transaction]:
        async with self.session() as session:
            transaction = (
                (
                    await session.execute(
                        select(Transactions).where(Transactions.id == id).options(joinedload(Transactions.messages))
                    )
                )
                .unique()
                .scalar_one_or_none()
            )
        return transaction.to_model() if transaction else None

    async def transactions_grouped_by_date(self, endpoint: Optional[str] = None) -> List[TransactionsGroupedByDate]:
        s_date = func.date(Transactions.started_at)

        query = select(
            # sqlite returns a string formated as "YYYY-MM-DD", postgres returns a datetime.date
            s_date,
            func.count(),
            func.sum(case((Transactions.x_status_class == "5xx", 1), else_=0)),
            func.avg(Transactions.elapsed),
        )

        if endpoint:
            query = query.where(Transactions.endpoint == endpoint)

        query = query.group_by(s_date).order_by(s_date.asc())
        async with self.session() as session:
            result = await session.execute(query)
            return [
                {
                    "date": ensure_date(row[0]),
                    "transactions": row[1],
                    "errors": row[2],
                    "meanDuration": row[3],
                }
                for row in result.fetchall()
            ]

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

        s_date = TruncDatetime(time_bucket, Transactions.started_at)
        query = select(
            s_date,
            func.count(),
            func.sum(case((Transactions.x_status_class == "5xx", 1), else_=0)),
            func.avg(Transactions.elapsed),
        )

        if endpoint:
            query = query.where(Transactions.endpoint == endpoint)

        if start_datetime:
            query = query.where(Transactions.started_at >= start_datetime)

        query = query.group_by(s_date).order_by(s_date.asc())
        async with self.session() as session:
            result = await session.execute(query)
            return [
                {
                    "datetime": ensure_datetime(row[0], UTC),
                    "count": row[1],
                    "errors": row[2],
                    "meanDuration": row[3],
                }
                for row in result.fetchall()
            ]

    async def get_blob(self, blob_id):
        """
        Retrieve a blob from the database, using its hash.
        Returns None if not found.

        :param blob_id: sha1 hash of the blob
        :return: Blob or None
        """
        async with self.session() as session:
            row = (
                await session.execute(
                    select(Blobs).where(Blobs.id == blob_id),
                )
            ).fetchone()

        if row:
            return Blob(id=blob_id, data=row[0].data, content_type=row[0].content_type)

    async def _on_startup_create_database(self, event: TransactionEvent):
        """Event handler to create the database tables on startup. May drop them first if configured to do so."""
        async with self.engine.begin() as conn:
            if self.settings.drop_tables:
                await conn.run_sync(self.metadata.drop_all)
            await conn.run_sync(self.metadata.create_all)

    async def _on_transaction_started(self, event: TransactionEvent):
        """Event handler to store the transaction in the database."""
        async with self.session() as session:
            transaction = Transactions()
            transaction.id = event.transaction.id
            transaction.type = event.transaction.type
            transaction.endpoint = event.transaction.endpoint
            transaction.started_at = event.transaction.started_at.astimezone(UTC).replace(tzinfo=None)
            transaction.x_method = event.transaction.extras.get("method")
            async with session.begin():
                session.add(transaction)

    async def _on_transaction_message(self, event: MessageEvent):
        transaction, message = event.transaction, event.message
        # todo is the "__headers__" dunder content type any good idea ? maybe it's just a waste of bytes.
        headers_blob = Blob.from_data(message.serialized_headers, content_type="__headers__")
        content_blob = Blob.from_data(message.serialized_body, content_type=message.headers.get("content-type"))

        def create_blob_storage_task(blob):
            async def store_blob():
                async with self.session() as session:
                    async with session.begin():
                        db_blob = Blobs()
                        db_blob.id = blob.id
                        db_blob.content_type = blob.content_type
                        db_blob.data = blob.data
                        session.add(db_blob)

            return store_blob

        await self.worker.push(create_blob_storage_task(headers_blob), ignore_errors=True)
        await self.worker.push(create_blob_storage_task(content_blob), ignore_errors=True)

        async def store_message():
            async with self.session() as session:
                async with session.begin():
                    session.add(
                        Messages.from_models(transaction, message, headers_blob, content_blob),
                    )

        await self.worker.push(store_message)

    async def _on_transaction_ended(self, event: TransactionEvent):
        async with self.session() as session:
            async with session.begin():
                await session.execute(
                    update(Transactions)
                    .where(Transactions.id == event.transaction.id)
                    .values(
                        finished_at=event.transaction.finished_at.astimezone(UTC).replace(tzinfo=None),
                        elapsed=event.transaction.elapsed,
                        x_status_class=event.transaction.extras.get("status_class"),
                    )
                )
