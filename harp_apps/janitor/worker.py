import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from prometheus_client import Counter, Gauge

from harp import get_logger
from harp.sweeps import Sweep, SweepRegistry
from harp_apps.storage.services import SqlStorage

from ..storage.models.blobs import CACHE_META_CONTENT_TYPE, ORPHAN_GRACE, cache_meta_references
from ..storage.types import IBlobStorage, IStorage
from .settings import JanitorSettings

logger = get_logger(__name__)

PROMETHEUS_GAUGES = {
    "storage.transactions": Gauge("storage_transactions", "Transactions currently in storage."),
    "storage.messages": Gauge("storage_messages", "Messages currently in storage."),
    "storage.blobs": Gauge("storage_blobs", "Blob objects currently in storage."),
    "storage.blobs.orphans": Gauge("storage_blobs_orphans", "Blobs referenced by no message and no HTTP cache entry."),
}

SWEEP_RUNS = Counter("janitor_sweep_runs", "Runs of a declared sweep.", ["sweep"])
SWEEP_FAILURES = Counter(
    "janitor_sweep_failures", "Runs of a declared sweep that failed or ran out of time.", ["sweep"]
)
SWEEP_ITEMS = Counter("janitor_sweep_items", "Items handled by a declared sweep.", ["sweep"])
SWEEP_DURATION = Gauge("janitor_sweep_duration_seconds", "Duration of the last run of a declared sweep.", ["sweep"])


@dataclass
class SweepStats:
    """What the janitor measured about one declared sweep."""

    runs: int = 0
    failures: int = 0
    items: int = 0
    last_duration: float | None = None
    last_error: str | None = None
    last_started: float | None = None


class JanitorWorker:
    #: Orphans written more recently than this are kept, see :data:`~harp_apps.storage.models.blobs.ORPHAN_GRACE`.
    orphan_grace: timedelta = ORPHAN_GRACE

    def __init__(
        self,
        storage: IStorage,
        blob_storage: IBlobStorage,
        settings: JanitorSettings,
        sweeps: SweepRegistry = None,
    ):
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.blob_storage: IBlobStorage = blob_storage
        self.settings = settings

        #: Sweeps declared by applications, the janitor schedules them without knowing who declared what.
        self.sweeps: SweepRegistry = sweeps if sweeps is not None else SweepRegistry()
        self.sweep_stats: dict[str, SweepStats] = {}
        self.clock = time.monotonic

        self.running = False
        self.session_factory = self.storage.session_factory
        self._running_lock = asyncio.Lock()

    def schedule(self):
        """
        Tell the registry that someone schedules the declared sweeps, so startup does not warn they will not run.
        """
        self.sweeps.mark_scheduled()

    def stop(self):
        """
        Mark the loop for termination.
        """
        self.running = False

    async def run(self):
        """
        Once dependencies are ready, start the main loop (basically, run the `loop()` every `period` seconds), until
        `stop()` is called.
        """
        # do not start before storage is ready
        async with self._running_lock:
            self.running = True

            while self.running:
                try:
                    await self.loop()
                except Exception as exc:
                    logger.exception(exc)
                await asyncio.sleep(self.settings.period)

    async def loop(self):
        """
        One iteration of the janitor loop.
        """

        await self.run_sweeps()

        await self.delete_orphan_blobs()

        # Compute and store stored objecg counts as metrics
        logger.debug("🧹 Compute and store metrics...")
        await self.compute_and_store_metrics()

    async def run_sweeps(self):
        """
        Run the declared sweeps that are due. A sweep that fails or runs out of time is counted, never stops the others.
        """
        for sweep in self.sweeps:
            stats = self.sweep_stats.setdefault(sweep.name, SweepStats())
            if self._is_due(sweep, stats):
                await self._run_sweep(sweep, stats)

    def _is_due(self, sweep: Sweep, stats: SweepStats) -> bool:
        if sweep.interval is None or stats.last_started is None:
            return True
        return self.clock() - stats.last_started >= sweep.interval.total_seconds()

    async def _run_sweep(self, sweep: Sweep, stats: SweepStats):
        started = stats.last_started = self.clock()
        stats.runs += 1
        SWEEP_RUNS.labels(sweep.name).inc()
        items = 0
        try:
            async with asyncio.timeout(sweep.budget.seconds) as deadline:
                items = await sweep.run(sweep.budget) or 0
        except Exception as exc:
            if deadline.expired():
                self._record_failure(sweep, stats, f"ran out of its time budget ({sweep.budget.seconds}s)")
            else:
                logger.exception(exc)
                self._record_failure(sweep, stats, f"{type(exc).__name__}: {exc}")
        else:
            stats.last_error = None
        stats.items += items
        stats.last_duration = self.clock() - started
        SWEEP_ITEMS.labels(sweep.name).inc(items)
        SWEEP_DURATION.labels(sweep.name).set(stats.last_duration)
        logger.debug("🧹 Sweep %s: %d items in %.3fs", sweep.name, items, stats.last_duration)

    @staticmethod
    def _record_failure(sweep: Sweep, stats: SweepStats, error: str):
        stats.failures += 1
        stats.last_error = error
        SWEEP_FAILURES.labels(sweep.name).inc()
        logger.warning("🧹 Sweep %s failed: %s", sweep.name, error)

    async def delete_orphan_blobs(self):
        """
        Find and remove blobs that are not referenced anymore by any transaction.
        """

        count = None

        if self.blob_storage.type == "sql":
            # A blob is an orphan when no message and no HTTP cache entry references it. Cache entries
            # themselves are reclaimed by the cache's TTL sweep, never here. Blobs written within the
            # grace period are kept: their message or cache entry may not be committed yet.
            older_than = datetime.now(UTC) - self.orphan_grace
            orphans = await self.storage.blobs.find_orphans(older_than=older_than)
            count = await self.storage.blobs.delete_orphans(orphans, older_than=older_than)
        elif self._lists_blob_ids:
            # Blobs of a backend that lives outside the SQL database: the same definition of an orphan, read from
            # the messages (SQL) and the cache entries (the backend), then deleted unless written within the grace.
            _, orphans = await self._find_unreferenced_blobs()
            count = await self.blob_storage.delete_stale(orphans, older_than=datetime.now(UTC) - self.orphan_grace)

        if count is None:
            # The blob storage may need to clean orphans but no implementation is available
            logger.debug("🧹 DeleteOrphanBlobs[%s] Not implemented.", self.blob_storage.type)
        else:
            logger.debug(
                "🧹 DeleteOrphanBlobs[%s] Removed %d blobs.",
                self.blob_storage.type,
                count,
            )

    @property
    def _lists_blob_ids(self) -> bool:
        return hasattr(self.blob_storage, "iter_blob_ids")

    async def _find_unreferenced_blobs(self, session=None) -> tuple[int, list[str]]:
        """Count the blobs of a backend that can list them, and find those nothing references.

        Ids are listed before the cache entries are read, so a blob stored in between is either seen as
        referenced or too young to be removed.
        """
        blob_ids = [blob_id async for blob_id in self.blob_storage.iter_blob_ids()]
        kept = set()
        async for meta in self.blob_storage.iter_blobs(CACHE_META_CONTENT_TYPE):
            kept.add(meta.id)
            kept |= cache_meta_references(meta.data)
        candidates = [blob_id for blob_id in blob_ids if blob_id not in kept]
        referenced = await self.storage.blobs.referenced_by_messages(candidates, session=session)
        return len(blob_ids), [blob_id for blob_id in candidates if blob_id not in referenced]

    async def compute_and_store_metrics(self):
        """
        Compute counts of objects in storage, and store them as metrics.
        """

        # TODO to storage

        values = await self.compute_metrics()
        async with self.session_factory() as session:
            await self.storage.metrics.insert_values(values, session=session)

    async def compute_metrics(self, session=None):
        """Counts of stored objects. Without a session, each count takes the connection only for its own query."""
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
            values["storage.blobs"], orphans = await self._find_unreferenced_blobs(session)
            values["storage.blobs.orphans"] = len(orphans)
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

        # TODO to storage
        return (
            await session.execute(
                getattr(
                    getattr(self.storage, name),
                    method,
                )()
            )
        ).scalar()
