from datetime import UTC
from functools import partial
from math import log10
from time import monotonic

from prometheus_client import Counter
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncEngine
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.http import get_serializer_for
from harp.models import Blob
from harp.models.transactions import encode_cache_flag, encode_markers
from harp.utils.background import AsyncWorkerQueue
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.constants import (
    SKIP_REQUEST_BODY_STORAGE,
    SKIP_REQUEST_HEADERS_STORAGE,
    SKIP_REQUEST_STORAGE,
    SKIP_RESPONSE_BODY_STORAGE,
    SKIP_RESPONSE_HEADERS_STORAGE,
    SKIP_RESPONSE_STORAGE,
    SHED_BODIES,
    SHED_HEADERS,
    SHED_MESSAGES,
    SKIP_STORAGE,
)
from harp_apps.storage.models import Message as SqlMessage
from harp_apps.storage.models import Transaction as SqlTransaction
from harp_apps.storage.types import IBlobStorage, IStorage

logger = get_logger(__name__)

DROPPED_COUNTER = Counter(
    "dropped",
    "Items the storage worker did not store because of queue pressure, by kind.",
    ["kind"],
)

DROPPED_KINDS = ("transactions", "messages", "headers", "bodies")

# Expose every series at 0 from startup, so alerts and rate() never face a missing series.
for _kind in DROPPED_KINDS:
    DROPPED_COUNTER.labels(_kind)


class StorageAsyncWorkerQueue(AsyncWorkerQueue):
    def __init__(self, engine: AsyncEngine, storage: IStorage, blob_storage: IBlobStorage):
        self.engine = engine
        self.storage = storage
        self.blob_storage = blob_storage
        super().__init__()
        self.seen = set()
        self._dropped_since_warning = dict.fromkeys(DROPPED_KINDS, 0)
        self._last_shed_warning_at = None

    #: Minimum delay (seconds) between two shedding warnings.
    shed_warning_interval = 10.0

    def _shed(self, kind: str):
        """Counts a dropped item and, at most once per interval, logs what was dropped since the last warning."""
        DROPPED_COUNTER.labels(kind).inc()
        self._dropped_since_warning[kind] += 1

        now = monotonic()
        if self._last_shed_warning_at is not None and now - self._last_shed_warning_at < self.shed_warning_interval:
            return

        counts = " ".join(f"{k}={v}" for k, v in self._dropped_since_warning.items())
        logger.warning(f"Storage under pressure (backlog ~{self._pressure}), dropped since last warning: {counts}")
        self._dropped_since_warning = dict.fromkeys(DROPPED_KINDS, 0)
        self._last_shed_warning_at = now

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
            self._shed("transactions")

        if SKIP_STORAGE in event.transaction.markers:
            return

        # Copy fields into a dict that won't change before the task is handled
        transaction_data = event.transaction.as_storable_dict(with_tags=True)

        async def create_transaction():
            return await self.storage.transactions.create(transaction_data)

        # Schedule
        await self.push(create_transaction)

    async def on_transaction_message(self, event: HttpMessageEvent):
        if SKIP_STORAGE in event.transaction.markers:
            return

        if self.pressure >= 3:
            event.transaction.markers.add(SHED_MESSAGES)
            self._shed("messages")
            return

        # Check if we should skip this entire message
        skip_message = (
            event.message.kind == "request"
            and SKIP_REQUEST_STORAGE in event.transaction.markers
            or event.message.kind == "response"
            and SKIP_RESPONSE_STORAGE in event.transaction.markers
        )
        if skip_message:
            logger.debug(
                f"Skipping storing {event.message.kind.capitalize()} message",
                transaction_id=event.transaction.id,
            )
            return

        await event.message.aread()
        serializer = get_serializer_for(event.message)

        message_data = {
            "transaction_id": event.transaction.id,
            "kind": event.message.kind,
            "summary": serializer.summary,
            "created_at": event.message.created_at,
        }

        # Check if we should skip headers
        skip_headers = (
            event.message.kind == "request"
            and SKIP_REQUEST_HEADERS_STORAGE in event.transaction.markers
            or event.message.kind == "response"
            and SKIP_RESPONSE_HEADERS_STORAGE in event.transaction.markers
        )

        # Eventually store the headers blob (later)
        if not skip_headers and self.pressure <= 2:
            headers_blob = await Blob.afrom_data(serializer.headers, content_type="http/headers")
            await self.push(partial(self.blob_storage.put, headers_blob), ignore_errors=True)
            message_data["headers"] = headers_blob.id
        elif not skip_headers:
            event.transaction.markers.add(SHED_HEADERS)
            self._shed("headers")
        else:
            logger.debug(
                f"Skipping storing {event.message.kind.capitalize()} headers",
                transaction_id=event.transaction.id,
                summary=serializer.summary,
            )

        # Check if we should skip body
        skip_body = (
            event.message.kind == "request"
            and SKIP_REQUEST_BODY_STORAGE in event.transaction.markers
            or event.message.kind == "response"
            and SKIP_RESPONSE_BODY_STORAGE in event.transaction.markers
        )

        # Eventually store the content blob (later)
        if not skip_body and self.pressure <= 1:
            content_blob = await Blob.afrom_data(
                serializer.body, content_type=event.message.headers.get("content-type")
            )
            await self.push(partial(self.blob_storage.put, content_blob), ignore_errors=True)
            message_data["body"] = content_blob.id
        elif not skip_body:
            event.transaction.markers.add(SHED_BODIES)
            self._shed("bodies")
        else:
            logger.debug(
                f"Skipping storing {event.message.kind.capitalize()} body",
                transaction_id=event.transaction.id,
                summary=serializer.summary,
            )

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
            "x_cached": encode_cache_flag(event.transaction.extras.get("cached")),
            "markers": encode_markers(event.transaction.markers),
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
