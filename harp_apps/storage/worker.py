import asyncio
from dataclasses import dataclass, field
from datetime import UTC
from math import log10
from time import monotonic

from prometheus_client import Counter
from sqlalchemy import insert, select, tuple_, update
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
from harp_apps.storage.models import Tag as SqlTag
from harp_apps.storage.models import TagValue as SqlTagValue
from harp_apps.storage.models import Transaction as SqlTransaction
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
from harp_apps.storage.models.transactions import transaction_tag_values_association_table
from harp_apps.storage.types import IBlobStorage, IStorage
from harp_apps.storage.utils.upsert import insert_ignoring_duplicates

logger = get_logger(__name__)

DROPPED_COUNTER = Counter(
    "dropped",
    "Items the storage worker did not store because of queue pressure, by kind.",
    ["kind"],
)

FLUSH_FAILURES_COUNTER = Counter(
    "storage_flush_failures",
    "Writes of ended transactions to the database that failed (a batch, then each transaction of it alone).",
)

DROPPED_KINDS = ("transactions", "messages", "headers", "bodies")

# Expose every series at 0 from startup, so alerts and rate() never face a missing series.
for _kind in DROPPED_KINDS:
    DROPPED_COUNTER.labels(_kind)


@dataclass
class PendingTransaction:
    """
    What the worker knows of a transaction until it is written: held in memory, written once when it ends, in a
    batch. Once inserted early, its payload (messages, blobs) is written and freed: only a light entry stays.
    """

    id: str
    data: dict
    tags: dict
    messages: list[dict] = field(default_factory=list)
    blobs: dict[str, Blob] = field(default_factory=dict)
    end_data: dict = field(default_factory=dict)
    inserted: bool = False
    ended: bool = False
    started_at: float = field(default_factory=monotonic)


class StorageAsyncWorkerQueue(AsyncWorkerQueue):
    def __init__(
        self,
        engine: AsyncEngine,
        storage: IStorage,
        blob_storage: IBlobStorage,
        early_insert_after: float = 1.0,
        pending_max_age: float = 3600.0,
        flush_interval: float = 1.0,
        flush_batch_size: int = 500,
    ):
        self.engine = engine
        self.storage = storage
        self.blob_storage = blob_storage
        #: Seconds after which a transaction still open is inserted, so that it can be seen while it runs.
        self.early_insert_after = early_insert_after
        #: Seconds after which the worker forgets a transaction that never ended (it stays as it was last written).
        self.pending_max_age = pending_max_age
        #: Ended transactions are written together, every ``flush_interval`` seconds or ``flush_batch_size`` of them.
        self.flush_interval = flush_interval
        self.flush_batch_size = flush_batch_size
        self._pending: dict[str, PendingTransaction] = {}
        self._ended: list[PendingTransaction] = []
        self._flush_queued = False
        super().__init__()
        self.seen = set()
        self._tick_handle = asyncio.get_running_loop().call_later(self.flush_interval, self._tick)
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
        # What waits to be written: the queue, and the ended transactions the next flush will take.
        self._pressure += len(getattr(self, "_ended", ()))

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

        self._ended.append(pending)
        if len(self._ended) >= self.flush_batch_size:
            self._schedule_flush()

    def take_pending(self, transaction) -> PendingTransaction | None:
        """Closes what the worker kept of an ended transaction, ready to be flushed. None if there is nothing to write."""
        pending = self._pending.pop(transaction.id, None)
        if pending is None:
            return None
        pending.ended = True

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

    def _tick(self):
        self._tick_handle = None
        if not self._running:
            return
        self._schedule_flush()
        self._tick_handle = asyncio.get_running_loop().call_later(self.flush_interval, self._tick)

    def _schedule_flush(self):
        """Queues one flush, unless one is already waiting: it takes everything ready when it runs."""
        if self._flush_queued or not self._running:
            return
        self._flush_queued = True
        self.push_nowait(self._flush_job)

    async def _flush_job(self):
        self._flush_queued = False
        ended, self._ended = self._ended, []
        self._pressure = self._queue.qsize() + len(ended)
        await self._flush_resiliently(ended + self._sweep())

    def _sweep(self) -> list[PendingTransaction]:
        """
        One pass over the transactions still open: forgets those silent for too long, and returns those running for
        longer than the early-insert threshold and not yet in the database, to be inserted with the batch.
        """
        now = monotonic()
        due = []
        for pending in list(self._pending.values()):
            age = now - pending.started_at
            if age >= self.pending_max_age:
                del self._pending[pending.id]
                logger.debug(
                    f"Transaction never ended, forgotten after {self.pending_max_age}s", transaction_id=pending.id
                )
            elif age >= self.early_insert_after and not pending.inserted:
                due.append(pending)
        return due

    async def wait_until_empty(self):
        """Waits until everything handed to the worker is written, ended transactions included."""
        if self._running:
            self._schedule_flush()
        await super().wait_until_empty()

    async def _flush_resiliently(self, pendings: list[PendingTransaction]):
        """Writes the batch; if it fails, logs and counts it, then tries each transaction alone so one cannot lose all."""
        try:
            await self._write(pendings)
            return
        except Exception:
            FLUSH_FAILURES_COUNTER.inc()
            logger.exception(f"Could not write a batch of {len(pendings)} transactions")
        if len(pendings) < 2:
            return
        for pending in pendings:
            try:
                await self._write([pending])
            except Exception:
                FLUSH_FAILURES_COUNTER.inc()
                logger.exception("Could not write a transaction", transaction_id=pending.id)

    async def flush(self, ended: list[PendingTransaction]):
        """Writes ended transactions, their messages and blobs, in one database transaction."""
        await self._write(ended)

    async def _write(self, pendings: list[PendingTransaction]):
        """
        Writes what the given transactions hold, in one database transaction: the transaction rows (inserted, or
        updated once inserted early), their messages, blobs and tags. Transactions still open are inserted
        unfinished and their payload is written and freed, so that one that never ends holds no payload.
        """
        if not pendings:
            return

        # Taken now: messages may arrive, and transactions end, while the write waits for the database.
        taken = [(pending, pending.messages, pending.blobs, pending.ended) for pending in pendings]
        end_data = [pending.end_data if pending.ended else {} for pending in pendings]
        for pending in pendings:
            pending.messages, pending.blobs = [], {}

        # MySQL keeps blobs apart: a blob too wide for its column must not take the transaction down with it.
        in_database = (
            isinstance(self.blob_storage, SqlBlobStorage)
            and self.blob_storage.engine is self.engine
            and self.engine.dialect.name != "mysql"
        )
        try:
            if not in_database:
                # Another blob storage: its writes cannot share the database transaction. A failed blob is logged and
                # the message keeps pointing at it, as before.
                for _, _, blobs, _ in taken:
                    for blob in blobs.values():
                        try:
                            await self.blob_storage.put(blob)
                        except Exception:
                            logger.exception(f"Could not store blob {blob.id}")

            transactions = SqlTransaction.__table__
            async with self.engine.begin() as conn:
                if in_database:
                    blobs = {blob.id: blob for _, _, blobs, _ in taken for blob in blobs.values()}
                    await self.blob_storage.put_in(conn, list(blobs.values()))

                to_insert = [{**p.data, **e} for p, e in zip(pendings, end_data) if not p.inserted]
                for pending, values in zip(pendings, end_data):
                    if pending.inserted and values:
                        await conn.execute(update(transactions).where(transactions.c.id == pending.id).values(**values))
                if to_insert:
                    await conn.execute(insert(transactions), to_insert)

                messages = [message for _, messages, _, _ in taken for message in messages]
                if messages:
                    await conn.execute(insert(SqlMessage.__table__), messages)

                await self._write_tags(conn, [p for p in pendings if p.tags])
        except BaseException:
            for pending, messages, blobs, _ in taken:  # nothing was written: keep it for the next write
                pending.messages = messages + pending.messages
                pending.blobs = {**blobs, **pending.blobs}
            raise

        for pending, _, _, finished in taken:
            pending.inserted = True
            pending.tags = {}
            if not finished:
                pending.data = {}  # the row is there: only what the end needs stays

    async def _write_tags(self, conn, pendings: list[PendingTransaction]):
        """Stores the tags, their values and the links to the transactions: a few statements for any number of them."""
        if not pendings:
            return
        dialect = conn.dialect.name
        names = {name for pending in pendings for name in pending.tags}
        await conn.execute(
            insert_ignoring_duplicates(dialect, SqlTag.__table__, ("name",)), [{"name": name} for name in names]
        )
        tag_ids = {
            row.name: row.id for row in await conn.execute(select(SqlTag.id, SqlTag.name).where(SqlTag.name.in_(names)))
        }

        pairs = {(tag_ids[name], str(value)) for pending in pendings for name, value in pending.tags.items()}
        await conn.execute(
            insert_ignoring_duplicates(dialect, SqlTagValue.__table__, ("tag_id", "value")),
            [{"tag_id": tag_id, "value": value} for tag_id, value in pairs],
        )
        value_ids = {
            (row.tag_id, row.value): row.id
            for row in await conn.execute(
                select(SqlTagValue.id, SqlTagValue.tag_id, SqlTagValue.value).where(
                    tuple_(SqlTagValue.tag_id, SqlTagValue.value).in_(list(pairs))
                )
            )
        }
        await conn.execute(
            insert_ignoring_duplicates(
                dialect, transaction_tag_values_association_table, ("transaction_id", "value_id")
            ),
            [
                {"transaction_id": pending.id, "value_id": value_ids[(tag_ids[name], str(value))]}
                for pending in pendings
                for name, value in pending.tags.items()
            ],
        )

    async def close(self):
        """
        Stops accepting work, flushes the transactions that ended and waits for the queue. Transactions still open
        are not: those older than the early-insert threshold are in the database already, unfinished (the last
        flush put them there), younger ones are lost (recording is best effort).
        """
        if self._tick_handle:
            self._tick_handle.cancel()
            self._tick_handle = None
        self._schedule_flush()
        await super().close()
