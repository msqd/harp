"""Sweeps declared by the storage application (see :mod:`harp.sweeps`): what keeps the storage from growing forever."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from prometheus_client import Gauge

from harp import get_logger
from harp.sweeps import Sweep, SweepBudget

from .models.blobs import ORPHAN_GRACE
from .services import SqlStorage
from .types import IBlobStorage, IStorage

logger = get_logger(__name__)

TRANSACTIONS_SWEEP = "storage.transactions"
ORPHAN_BLOBS_SWEEP = "storage.blobs.orphans"
METRICS_SWEEP = "storage.metrics"

PROMETHEUS_GAUGES = {
    "storage.transactions": Gauge("storage_transactions", "Transactions currently in storage."),
    "storage.messages": Gauge("storage_messages", "Messages currently in storage."),
    "storage.blobs": Gauge("storage_blobs", "Blob objects currently in storage."),
    "storage.blobs.orphans": Gauge("storage_blobs_orphans", "Blobs referenced by no message."),
}


#: How many blob ids a sweep holds, looks up and deletes at once for a blob backend that lives outside SQL.
BLOB_BATCH_SIZE = 500


@dataclass(frozen=True)
class _BlobPass:
    blobs: int
    orphans: int
    deleted: int = 0

    @property
    def after_deletion(self) -> "BlobSweep":
        return BlobSweep(self.blobs - self.deleted, self.orphans - self.deleted)


@dataclass(frozen=True)
class BlobSweep:
    """What one pass over a blob backend found, after its deletions: blobs still stored, and orphans among them."""

    blobs: int
    orphans: int


class StorageSweeps:
    """The storage's periodic cleanups: retention, orphan blobs, and the figures of what is stored."""

    #: Blob ids handled per batch with a backend that lists its blobs, see :data:`BLOB_BATCH_SIZE`.
    batch_size: int = BLOB_BATCH_SIZE

    #: Orphans written more recently than this are kept, see :data:`~harp_apps.storage.models.blobs.ORPHAN_GRACE`.
    orphan_grace: timedelta = ORPHAN_GRACE

    def __init__(self, storage: IStorage, blob_storage: IBlobStorage, retention: timedelta):
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.blob_storage: IBlobStorage = blob_storage
        self.retention = retention
        self.session_factory = self.storage.session_factory

        #: What the last orphan sweep left in a backend that lists its blobs, so the metrics need not list them again.
        self._last_blob_sweep: BlobSweep | None = None

    def sweeps(self) -> list[Sweep]:
        """The sweeps to declare, in the order they must run."""
        return [
            Sweep(name=name, interval=None, budget=SweepBudget(), run=run)
            for name, run in (
                (TRANSACTIONS_SWEEP, self.purge_old_transactions),
                (ORPHAN_BLOBS_SWEEP, self.delete_orphan_blobs),
                (METRICS_SWEEP, self.compute_and_store_metrics),
            )
        ]

    async def purge_old_transactions(self, budget: SweepBudget | None = None) -> int:
        """
        Remove transactions older than the retention period, except flagged ones. The database cascades the deletion
        to messages and tag values; their blobs are then freed by the orphan sweep.
        """
        count = await self.storage.transactions.purge_old(self.retention)
        if count:
            logger.debug("🧹 Deleted %d old transactions", count)
        return count

    async def delete_orphan_blobs(self, budget: SweepBudget | None = None) -> int:
        """
        Find and remove blobs that are not referenced anymore by any transaction.
        """

        count = None

        if self.blob_storage.type == "sql":
            # A blob is an orphan when no message references it. Blobs written within the grace period are
            # kept: their message may not be committed yet.
            older_than = datetime.now(UTC) - self.orphan_grace
            orphans = await self.storage.blobs.find_orphans(older_than=older_than)
            count = await self.storage.blobs.delete_orphans(orphans, older_than=older_than)
        elif self._lists_blob_ids:
            # Blobs of a backend that lives outside the SQL database: the same definition of an orphan, read from
            # the messages (SQL), then deleted unless written within the grace.
            blob_pass = await self._sweep_blobs(older_than=datetime.now(UTC) - self.orphan_grace)
            count = blob_pass.deleted
            self._last_blob_sweep = blob_pass.after_deletion

        if count is None:
            # The blob storage may need to clean orphans but no implementation is available
            logger.debug("🧹 DeleteOrphanBlobs[%s] Not implemented.", self.blob_storage.type)
            return 0

        logger.debug("🧹 DeleteOrphanBlobs[%s] Removed %d blobs.", self.blob_storage.type, count)
        return count

    @property
    def _lists_blob_ids(self) -> bool:
        return hasattr(self.blob_storage, "iter_blob_ids")

    async def _sweep_blobs(self, *, older_than: datetime | None = None, session=None) -> _BlobPass:
        """Count the blobs of a backend that can list them, and find those nothing references.

        Streams the blobs, batch by batch. With `older_than`, each batch's orphans are deleted (unless written since)
        before the next batch is read. Memory holds one batch, never the blob ids.
        """
        total = orphans = deleted = 0
        batch: list[str] = []
        async for blob_id in self.blob_storage.iter_blob_ids():
            batch.append(blob_id)
            if len(batch) >= self.batch_size:
                size, found, removed = await self._sweep_batch(batch, older_than, session)
                total, orphans, deleted = total + size, orphans + found, deleted + removed
                batch = []
        size, found, removed = await self._sweep_batch(batch, older_than, session)
        return _BlobPass(total + size, orphans + found, deleted + removed)

    async def _sweep_batch(self, batch: list[str], older_than, session) -> tuple[int, int, int]:
        """The size of a batch of ids, its orphans, and how many of them were deleted.

        ``SCAN`` may return a key more than once: a batch counts each id once (a repeat in another batch still can't be
        told, without holding every id).
        """
        batch = list(dict.fromkeys(batch))
        if not batch:
            return 0, 0, 0
        referenced = await self.storage.blobs.referenced_by_messages(batch, session=session)
        orphans = [blob_id for blob_id in batch if blob_id not in referenced]
        deleted = 0
        if older_than is not None and orphans:
            deleted = await self.blob_storage.delete_stale(orphans, older_than=older_than)
        return len(batch), len(orphans), deleted

    async def compute_and_store_metrics(self, budget: SweepBudget | None = None) -> int:
        """
        Compute counts of objects in storage, and store them as metrics.
        """
        logger.debug("🧹 Compute and store metrics...")
        blob_sweep, self._last_blob_sweep = self._last_blob_sweep, None
        values = await self.compute_metrics(blob_sweep=blob_sweep)
        async with self.session_factory() as session:
            await self.storage.metrics.insert_values(values, session=session)
        return len(values)

    async def compute_metrics(self, session=None, *, blob_sweep: BlobSweep | None = None):
        """Counts of stored objects. Without a session, each count takes the connection only for its own query.

        A backend that lists its blobs is listed again, unless the pass that just cleaned it is given."""
        values = {}
        counted = [("storage.transactions", "transactions"), ("storage.messages", "messages")]
        if not self._lists_blob_ids:
            counted.append(("storage.blobs", "blobs"))  # the blobs table is where this backend keeps them
        for key, name in counted:
            if session is not None:
                values[key] = await self.do_count(session, name)
            else:
                async with self.session_factory() as own:
                    values[key] = await self.do_count(own, name)
        if self._lists_blob_ids:
            found = blob_sweep or (await self._sweep_blobs(session=session)).after_deletion
            values["storage.blobs"], values["storage.blobs.orphans"] = found.blobs, found.orphans
        else:
            values["storage.blobs.orphans"] = await self.storage.blobs.count_orphans(session=session)

        for key, value in values.items():
            PROMETHEUS_GAUGES[key].set(value)

        return values

    async def do_count(self, session, name: str, /, *, method="count"):
        """
        Helper to count objects in storage, from different repositories and using different methods for building the
        actual query.

        :param session: sqlalchemy async session
        :param name: repository name (should be available from storage)
        :param method: method name to call on the repository to get the actual sqlalchemy query, default as "count"
        :return: integer
        """
        return (
            await session.execute(
                getattr(
                    getattr(self.storage, name),
                    method,
                )()
            )
        ).scalar()
