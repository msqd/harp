from datetime import UTC, date, datetime
from typing import AsyncIterator, List, Optional, TypedDict

from sqlalchemy import alias, case, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.tables import BlobsTable, MessagesTable, TransactionsTable, metadata
from harp.core.asgi.events import EVENT_CORE_STARTED, MessageEvent, TransactionEvent
from harp.core.models.messages import Blob, Message
from harp.core.models.transactions import Transaction


class TransactionsGroupedByDate(TypedDict):
    date: date
    transactions: int
    errors: int
    meanDuration: float


t_transactions = alias(TransactionsTable, name="t")
t_messages = alias(MessagesTable, name="m")
LEN_TRANSACTIONS_COLUMNS = len(TransactionsTable.columns)

logger = get_logger(__name__)

_FILTER_COLUMN_NAMES = {
    "method": "x_method",
    "status": "x_status_class",
}


def _filter_query(query, name, values):
    if values and values != "*":
        query = query.filter(
            getattr(
                t_transactions.c,
                _FILTER_COLUMN_NAMES.get(name, name),
            ).in_(values)
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
        self.engine = create_async_engine(self.settings.url, echo=self.settings.echo)
        self.metadata = metadata

        dispatcher.add_listener(EVENT_CORE_STARTED, self._on_startup_create_database, priority=-20)
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self._on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self._on_transaction_ended)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self._on_transaction_message)

    def connect(self):
        """Shortcut to get a connection from the engine.

        Example::

            async with self.connect() as conn:
                result = await conn.execute(...)

        """
        return self.engine.connect()

    def begin(self):
        """Shortcut to get a transaction from the engine (similar to :meth:`connect`, but with a database transaction).

        Example::

            async with self.begin() as conn:
                result = await conn.execute(...)

        """
        return self.engine.begin()

    async def get_facet_meta(self, name):
        if name == "endpoint":
            # get transaction count grouped by endpoint
            query = select(t_transactions.c.endpoint, func.count()).group_by(t_transactions.c.endpoint)
            async with self.connect() as conn:
                result = await conn.execute(query)
                return {row[0]: row[1] for row in result.fetchall()}

        raise NotImplementedError(f"Unknown facet: {name}")

    async def find_transactions(self, *, with_messages=False, filters=None) -> AsyncIterator[Transaction]:
        """
        Implements :meth:`IStorage.find_transactions <harp.protocols.storage.IStorage.find_transactions>`.

        :param with_messages:
        :return:

        """
        query = select(t_transactions, t_messages)
        if with_messages:
            # query.add_columns(messages)
            query = query.outerjoin(t_messages, t_messages.c.transaction_id == t_transactions.c.id)

        if filters:
            query = _filter_query(query, "endpoint", filters.get("endpoint", None))
            query = _filter_query(query, "method", filters.get("method", None))
            query = _filter_query(query, "status", filters.get("status", None))

        query = query.order_by(t_transactions.c.started_at.desc()).limit(50)

        current_transaction = None
        async with self.connect() as conn:
            result = await conn.execute(query)
            for row in result.fetchall():
                # not the same transaction, build new one
                if current_transaction is None or current_transaction.id != row[0]:
                    _db_transaction = row[0:LEN_TRANSACTIONS_COLUMNS]
                    if current_transaction:
                        yield current_transaction
                    # TODO WARNING the field order is not the same as the model
                    current_transaction = Transaction(
                        id=_db_transaction[0],
                        type=_db_transaction[1],
                        endpoint=_db_transaction[2],
                        started_at=_db_transaction[3],
                        finished_at=_db_transaction[4],
                        elapsed=_db_transaction[5],
                        messages=[],
                    )

                if with_messages and row[LEN_TRANSACTIONS_COLUMNS]:
                    _db_message = row[LEN_TRANSACTIONS_COLUMNS:]
                    current_transaction.messages.append(
                        Message(
                            id=_db_message[0],
                            transaction_id=_db_message[1],
                            kind=_db_message[2],
                            summary=_db_message[3],
                            headers=_db_message[4],
                            body=_db_message[5],
                            created_at=_db_message[6],
                        )
                    )

            if current_transaction:
                yield current_transaction

    async def transactions_grouped_by_date(self, endpoint: Optional[str] = None) -> List[TransactionsGroupedByDate]:
        query = select(
            func.date(t_transactions.c.started_at),  #! returns a string in sqlite of the formm "YYYY-MM-DD"
            func.count(),
            func.sum(case((t_transactions.c.x_status_class != "2xx", 1), else_=0)),
            func.avg(t_transactions.c.elapsed),
        )

        if endpoint:
            query = query.where(t_transactions.c.endpoint == endpoint)

        query = query.group_by(func.date(t_transactions.c.started_at))
        async with self.connect() as conn:
            result = await conn.execute(query)
            return [
                {
                    "date": datetime.strptime(row[0], "%Y-%m-%d").date(),
                    "transactions": row[1],
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
        async with self.connect() as conn:
            row = (await conn.execute(BlobsTable.select().where(BlobsTable.c.id == blob_id))).fetchone()

        if row:
            return Blob(id=row.id, data=row.data, content_type=row.content_type)

    async def store_blob(self, conn, blob: Blob):
        # todo this has concurrency problems with sqlite AND with postgres. Find a way to lock the insertion ? Or maybe
        # use an insert or update if not found, which will work by overriding just inserted data with the same data. But
        # this can be problematic under pressure, so maybe not.
        query = select(func.count()).where(BlobsTable.c.id == blob.id)
        if not await conn.scalar(query):
            from sqlite3 import IntegrityError

            from asyncpg import UniqueViolationError

            try:
                await conn.execute(
                    BlobsTable.insert().values(id=blob.id, data=blob.data, content_type=blob.content_type)
                )
            except IntegrityError as e:
                logger.error(
                    "SQLite IntegrityError: %s (ignored for now as it just shows concurrency problems with sqlite, "
                    "which we are aware of)",
                    e,
                )
            except UniqueViolationError as e:
                logger.error("Postgres UniqueViolationError: %s", e)
        return hash

    async def _on_startup_create_database(self, event: TransactionEvent):
        """Event handler to create the database tables on startup. May drop them first if configured to do so."""
        async with self.begin() as conn:
            if self.settings.drop_tables:
                await conn.run_sync(metadata.drop_all)
            await conn.run_sync(metadata.create_all)

    async def _on_transaction_started(self, event: TransactionEvent):
        """Event handler to store the transaction in the database."""
        async with self.begin() as conn:
            await conn.execute(
                TransactionsTable.insert().values(
                    id=event.transaction.id,
                    type=event.transaction.type,
                    endpoint=event.transaction.endpoint,
                    started_at=event.transaction.started_at.astimezone(UTC).replace(tzinfo=None),
                    x_method=event.transaction.extras.get("method"),
                )
            )

    async def _on_transaction_message(self, event: MessageEvent):
        async with self.begin() as conn:
            # todo is the "__headers__" dunder content type any good idea ? maybe it's just a waste of bytes.
            headers_blob = Blob.from_data(event.message.serialized_headers, content_type="__headers__")

            content_blob = Blob.from_data(
                event.message.serialized_body, content_type=event.message.headers.get("content-type")
            )

            # todo compute hash now, store later ? (once benchmarks are up)
            await self.store_blob(conn, headers_blob)
            await self.store_blob(conn, content_blob)

            await conn.execute(
                MessagesTable.insert().values(
                    transaction_id=event.transaction.id,
                    kind=event.message.kind,
                    summary=event.message.serialized_summary,
                    headers=headers_blob.id,
                    body=content_blob.id,
                    created_at=event.message.created_at.astimezone(UTC).replace(tzinfo=None),
                )
            )

    async def _on_transaction_ended(self, event: TransactionEvent):
        async with self.begin() as conn:
            await conn.execute(
                TransactionsTable.update()
                .where(TransactionsTable.c.id == event.transaction.id)
                .values(
                    finished_at=event.transaction.finished_at.astimezone(UTC).replace(tzinfo=None),
                    elapsed=event.transaction.elapsed,
                    x_status_class=event.transaction.extras.get("status_class"),
                )
            )
