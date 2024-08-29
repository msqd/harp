from datetime import UTC
from functools import partial
from math import log10

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncEngine
from whistle import IAsyncEventDispatcher

from harp.http import get_serializer_for
from harp.models import Blob
from harp.utils.background import AsyncWorkerQueue
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.models import Message as SqlMessage
from harp_apps.storage.models import Transaction as SqlTransaction
from harp_apps.storage.types import IBlobStorage, IStorage

SKIP_STORAGE = "skip-storage"


class StorageAsyncWorkerQueue(AsyncWorkerQueue):
    def __init__(self, engine: AsyncEngine, storage: IStorage, blob_storage: IBlobStorage):
        self.engine = engine
        self.storage = storage
        self.blob_storage = blob_storage
        super().__init__()
        self.seen = set()

    def register_events(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, self.on_transaction_started)
        dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, self.on_transaction_message)
        dispatcher.add_listener(EVENT_TRANSACTION_ENDED, self.on_transaction_ended)

    def cleanup(self):
        super().cleanup()

    @property
    def pressure(self):
        if self._pressure <= 1:
            return 0
        return int(log10(self._pressure))

    async def on_transaction_started(self, event: TransactionEvent):
        """Event handler to store the transaction in the database."""

        if self.pressure >= 4:
            event.transaction.markers.add(SKIP_STORAGE)
            return

        # Copy fields into a dict that won't change before the task is handled
        transaction_data = event.transaction.as_storable_dict(with_tags=True)

        async def create_transaction():
            return await self.storage.transactions.create(transaction_data)

        # Schedule
        await self.push(create_transaction)

    async def on_transaction_message(self, event: HttpMessageEvent):
        if SKIP_STORAGE in event.transaction.markers or self.pressure >= 3:
            return

        await event.message.aread()
        serializer = get_serializer_for(event.message)

        message_data = {
            "transaction_id": event.transaction.id,
            "kind": event.message.kind,
            "summary": serializer.summary,
            "created_at": event.message.created_at,
        }

        # Eventually store the headers blob (later)
        if self.pressure <= 2:
            headers_blob = Blob.from_data(serializer.headers, content_type="http/headers")
            await self.push(partial(self.blob_storage.put, headers_blob), ignore_errors=True)
            message_data["headers"] = headers_blob.id

        # Eventually store the content blob (later)
        if self.pressure <= 1:
            content_blob = Blob.from_data(serializer.body, content_type=event.message.headers.get("content-type"))
            await self.push(partial(self.blob_storage.put, content_blob), ignore_errors=True)
            message_data["body"] = content_blob.id

        async def create_message():
            async with self.engine.connect() as conn:
                await conn.execute(insert(SqlMessage).values(**message_data))
                await conn.commit()

        await self.push(create_message)

    async def on_transaction_ended(self, event: TransactionEvent):
        if SKIP_STORAGE in event.transaction.markers:
            return

        transaction_id = event.transaction.id
        transaction_data = {
            "finished_at": event.transaction.finished_at.astimezone(UTC),
            "elapsed": event.transaction.elapsed,
            "tpdex": event.transaction.tpdex,
            "x_status_class": event.transaction.extras.get("status_class"),
            "x_cached": event.transaction.extras.get("cached"),
        }

        async def update_transaction():
            async with self.engine.connect() as conn:
                await conn.execute(
                    update(SqlTransaction)
                    .where(
                        SqlTransaction.id == transaction_id,
                    )
                    .values(**transaction_data)
                )
                await conn.commit()

        await self.push(update_transaction)
