import asyncio
from dataclasses import dataclass, field
from datetime import UTC
from functools import partial
from math import log10
from time import monotonic
from types import SimpleNamespace

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
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
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


@dataclass
class PendingTransaction:
    """What the worker knows of a transaction until it is written: held in memory, written once when it ends."""

    id: str
    data: dict
    tags: dict
    messages: list[dict] = field(default_factory=list)
    blobs: dict[str, Blob] = field(default_factory=dict)
    end_data: dict = field(default_factory=dict)
    inserted: bool = False
    ended: bool = False
    tags_written: bool = False
    timer: asyncio.TimerHandle | None = None


class StorageAsyncWorkerQueue(AsyncWorkerQueue):
    def __init__(
        self, engine: AsyncEngine, storage: IStorage, blob_storage: IBlobStorage, early_insert_after: float = 1.0
    ):
        self.engine = engine
        self.storage = storage
        self.blob_storage = blob_storage
        #: Seconds after which a transaction still open is inserted, so that it can be seen while it runs.
        self.early_insert_after = early_insert_after
        super().__init__()
        self.seen = set()
        self._pending: dict[str, PendingTransaction] = {}
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

        # Copy fields into a dict that won't change while the transaction runs
        pending = PendingTransaction(
            id=event.transaction.id,
            data=event.transaction.as_storable_dict(),
            tags=dict(event.transaction.tags or {}),
        )
        self._pending[pending.id] = pending
        pending.timer = asyncio.get_running_loop().call_later(self.early_insert_after, self._early_insert_due, pending)

    def _early_insert_due(self, pending: PendingTransaction):
        pending.timer = None
        if pending.ended or not self._running:
            return

        async def insert_early():
            if pending.ended or pending.inserted:
                return
            await self.flush_insert(pending)

        self.push_nowait(insert_early)

    async def on_transaction_message(self, event: HttpMessageEvent):
        if SKIP_STORAGE in event.transaction.markers:
            return

        # A message for a transaction the worker never saw start has nowhere to go: handled, then dropped.
        pending = self._pending.get(event.transaction.id) or PendingTransaction(event.transaction.id, {}, {})

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
            # always present, so that messages of a transaction share the keys of one multi-row insert
            "headers": None,
            "body": None,
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
            pending.blobs[headers_blob.id] = headers_blob
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
            pending.blobs[content_blob.id] = content_blob
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

        pending.messages.append(message_data)

    async def on_transaction_ended(self, event: TransactionEvent):
        pending = self.take_pending(event.transaction)
        if pending is None:
            return

        await self.push(partial(self.flush, [pending]))

    def take_pending(self, transaction) -> PendingTransaction | None:
        """Closes what the worker kept of an ended transaction, ready to be flushed. None if there is nothing to write."""
        pending = self._pending.pop(transaction.id, None)
        if pending is None:
            return None
        pending.ended = True
        if pending.timer:
            pending.timer.cancel()
            pending.timer = None

        if SKIP_STORAGE in transaction.markers:
            return None

        pending.end_data = {
            "finished_at": transaction.finished_at.astimezone(UTC),
            "elapsed": transaction.elapsed,
            "tpdex": transaction.tpdex,
            "x_status_class": transaction.extras.get("status_class"),
            "x_cached": encode_cache_flag(transaction.extras.get("cached")),
            "markers": encode_markers(transaction.markers),
        }
        return pending

    async def flush(self, ended: list[PendingTransaction]):
        """Writes ended transactions, their messages and blobs, in one database transaction."""
        if not ended:
            return

        in_database = isinstance(self.blob_storage, SqlBlobStorage) and self.blob_storage.engine is self.engine
        if not in_database:
            # Another blob storage: its writes cannot share the database transaction.
            for pending in ended:
                for blob in pending.blobs.values():
                    await self.blob_storage.put(blob)

        transactions = SqlTransaction.__table__
        async with self.engine.begin() as conn:
            if in_database:
                blobs = {blob.id: blob for pending in ended for blob in pending.blobs.values()}
                await self.blob_storage.put_in(conn, list(blobs.values()))

            to_insert = [{**p.data, **p.end_data} for p in ended if not p.inserted]
            for pending in ended:
                if pending.inserted:
                    await conn.execute(
                        update(transactions).where(transactions.c.id == pending.id).values(**pending.end_data)
                    )
            if to_insert:
                await conn.execute(insert(transactions), to_insert)

            messages = [message for pending in ended for message in pending.messages]
            if messages:
                await conn.execute(insert(SqlMessage.__table__), messages)

        for pending in ended:
            await self._write_tags(pending)

    async def flush_insert(self, pending: PendingTransaction):
        """Inserts a transaction that is still running, so that it can be seen; its end will update it."""
        async with self.engine.begin() as conn:
            await conn.execute(insert(SqlTransaction.__table__), [pending.data])
        pending.inserted = True
        await self._write_tags(pending)

    async def _write_tags(self, pending: PendingTransaction):
        if pending.tags and not pending.tags_written:
            pending.tags_written = True
            await self.storage.transactions.set_tags(SimpleNamespace(id=pending.id), pending.tags)

    async def close(self):
        for pending in self._pending.values():
            if pending.timer:
                pending.timer.cancel()
                pending.timer = None
        await super().close()
