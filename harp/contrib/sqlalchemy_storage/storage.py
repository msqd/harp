from datetime import UTC, datetime
from typing import Iterable, List, Optional, TypedDict

from sqlalchemy import case, delete, func, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.contrib.sqlalchemy_storage.constants import TimeBucket
from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.utils.dates import TruncDatetime
from harp.core.asgi.events import EVENT_CORE_STARTED, MessageEvent, TransactionEvent
from harp.core.models.blobs import Blob as BlobModel
from harp.core.models.transactions import Transaction as TransactionModel
from harp.settings import PAGE_SIZE
from harp.utils.background import AsyncWorkerQueue
from harp.utils.dates import ensure_datetime

from .models import (
    FLAGS_BY_NAME,
    Base,
    Blob,
    Message,
    Results,
    TagsRepository,
    Transaction,
    TransactionsRepository,
    User,
    UserFlag,
    UsersRepository,
)
from .models.tags import TagValuesRepository
from .models.transactions import transaction_tag_values_association_table


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

        self.metadata = Base.metadata
        self.engine = create_async_engine(self.settings.url, echo=self.settings.echo)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)

        dispatcher.add_listener(EVENT_CORE_STARTED, self._on_startup_actions, priority=-20)
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self._on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self._on_transaction_ended)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self._on_transaction_message)

        self._is_db_set = False
        self._worker = None

        self.transactions = TransactionsRepository(self.session)
        self.users = UsersRepository(self.session)
        self.tags = TagsRepository(self.session)
        self.tag_values = TagValuesRepository(self.session)

    @property
    def worker(self):
        if not self._worker:
            self._worker = AsyncWorkerQueue()
        return self._worker

    async def get_facet_meta(self, name):
        if name == "endpoint":
            # get transaction count grouped by endpoint
            async with self.session() as session:
                query = select(Transaction.endpoint, func.count()).group_by(Transaction.endpoint)
                result = await session.execute(query)
                return {row[0]: row[1] for row in result.fetchall()}

        raise NotImplementedError(f"Unknown facet: {name}")

    async def get_transaction_list(
        self,
        *,
        with_messages=False,
        filters=None,
        page: int = 1,
        cursor: str = "",
        username: Optional[str] = None,
    ) -> Results[TransactionModel]:
        """
        Implements :meth:`Storage.find_transactions <harp.protocols.storage.Storage.find_transactions>`.

        :param with_messages:
        :return:

        """

        user = await self.users.find_one_by_username(username)

        result = Results()
        query = self.transactions.select(
            with_messages=with_messages,
            with_user_flags=user.id if user else False,
        )

        if filters:
            query = _filter_query(query, "endpoint", filters.get("endpoint", None))
            query = _filter_query(query, "method", filters.get("method", None))
            query = _filter_query(query, "status", filters.get("status", None))
            query = _filter_query_for_user_flags(query, filters.get("flag", None), user_id=user.id)

        query = query.order_by(Transaction.started_at.desc())

        # apply cursor (before count)
        if page and cursor:
            query = query.filter(Transaction.id <= cursor)

        async with self.session() as session:
            # count items from query
            result.meta["total"] = await session.scalar(
                query.with_only_columns(func.count(Transaction.id)).order_by(None)
            )

        # apply limit/offset (after count)
        query = query.limit(PAGE_SIZE)
        if page:
            query = query.offset(max(0, (page - 1) * PAGE_SIZE))

        async with self.session() as session:
            for transaction in (await session.scalars(query)).unique().all():
                result.append(transaction.to_model(with_user_flags=True))

        return result

    async def get_transaction(
        self,
        id: str,
        /,
        *,
        username: Optional[str] = None,
    ) -> Optional[TransactionModel]:
        user = await self.users.find_one_by_username(username)

        return (
            await self.transactions.find_one_by_id(
                id,
                with_messages=True,
                with_user_flags=user.id if user else False,
            )
        ).to_model(with_user_flags=True)

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
            func.sum(case((Transaction.x_status_class == "5xx", 1), else_=0)),
            func.avg(Transaction.elapsed),
        )

        if endpoint:
            query = query.where(Transaction.endpoint == endpoint)

        if start_datetime:
            query = query.where(Transaction.started_at >= start_datetime.astimezone(UTC).replace(tzinfo=None))

        query = query.group_by(s_date).order_by(s_date.asc())
        async with self.session() as session:
            result = await session.execute(query)
            return [
                {
                    "datetime": ensure_datetime(row[0], UTC),
                    "count": row[1],
                    "errors": row[2],
                    "meanDuration": row[3] if row[3] else 0,
                    # ! probably sqlite struggling with unfinished transactions
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
                    select(Blob).where(Blob.id == blob_id),
                )
            ).fetchone()

        if row:
            return BlobModel(id=blob_id, data=row[0].data, content_type=row[0].content_type)

    async def initialize(self, /, *, force_reset=False):
        """Create the database tables. May drop them first if configured to do so."""
        async with self.engine.begin() as conn:
            if force_reset or self.settings.drop_tables:
                await conn.run_sync(self.metadata.drop_all)
            await conn.run_sync(self.metadata.create_all)

    async def _on_startup_actions(self, TransactionEvent):
        """Event handler to create the database tables on startup. May drop them first if configured to do so."""
        await self.initialize()
        await self.create_users(["anonymous"])

    async def create_transaction(self, transaction: TransactionModel):
        async with self.session() as session:
            db_transaction = Transaction(
                id=transaction.id,
                type=transaction.type,
                endpoint=transaction.endpoint,
                started_at=transaction.started_at.astimezone(UTC).replace(tzinfo=None),
                x_method=transaction.extras.get("method"),
            )
            session.add(db_transaction)
            await session.commit()
        return db_transaction

    async def _on_transaction_started(self, event: TransactionEvent):
        """Event handler to store the transaction in the database."""
        return await self.create_transaction(event.transaction)

    async def set_user_flag(self, *, transaction_id: str, username: str, flag: int, value=True):
        """Sets or unsets a user flag on a transaction."""
        async with self.session() as session:
            async with session.begin():
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

    async def set_transaction_tags(self, transaction_id, tags: dict, /):
        async with self.session() as session:
            db_transaction = await self.transactions.find_one_by_id(transaction_id, session=session)

            values = []
            for name, value in tags.items():
                db_tag = await self.tags.find_or_create_one({"name": name}, session=session)
                db_value = await self.tag_values.find_or_create_one(
                    {"tag_id": db_tag.id, "value": value}, session=session
                )
                values.append(
                    {
                        "transaction_id": db_transaction.id,
                        "value_id": db_value.id,
                    }
                )

            if len(values):
                print(values)
                await session.execute(insert(transaction_tag_values_association_table), values)
                await session.commit()

        return db_transaction

    async def _on_transaction_message(self, event: MessageEvent):
        transaction, message = event.transaction, event.message
        # todo is the "__headers__" dunder content type any good idea ? maybe it's just a waste of bytes.
        headers_blob = BlobModel.from_data(message.serialized_headers, content_type="__headers__")
        content_blob = BlobModel.from_data(message.serialized_body, content_type=message.headers.get("content-type"))

        def create_blob_storage_task(blob):
            async def store_blob():
                async with self.session() as session:
                    async with session.begin():
                        db_blob = Blob()
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
                        Message.from_models(transaction, message, headers_blob, content_blob),
                    )

        await self.worker.push(store_message)

    async def _on_transaction_ended(self, event: TransactionEvent):
        async with self.session() as session:
            async with session.begin():
                await session.execute(
                    update(Transaction)
                    .where(Transaction.id == event.transaction.id)
                    .values(
                        finished_at=event.transaction.finished_at.astimezone(UTC).replace(tzinfo=None),
                        elapsed=event.transaction.elapsed,
                        x_status_class=event.transaction.extras.get("status_class"),
                    )
                )

    async def create_users(self, users: Iterable[str]):
        async with self.session() as session:
            async with session.begin():
                for username in users:
                    # Check if the username already exists
                    result = await session.execute(select(User).where(User.username == username))
                    existing_user = result.scalar_one_or_none()

                    # If the username does not exist, create a new user
                    if existing_user is None:
                        user = User()
                        user.username = username
                        session.add(user)
