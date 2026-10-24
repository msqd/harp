import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast

from prometheus_client import Gauge

from harp import get_logger
from harp_apps.storage.services import SqlStorage

from ..storage.models.base import with_session
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


class JanitorWorker:
    #: Orphans written more recently than this are kept, see :data:`~harp_apps.storage.models.blobs.ORPHAN_GRACE`.
    orphan_grace: timedelta = ORPHAN_GRACE

    def __init__(self, storage: IStorage, blob_storage: IBlobStorage, settings: JanitorSettings):
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.blob_storage: IBlobStorage = blob_storage
        self.settings = settings

        self.running = False
        self.session_factory = self.storage.session_factory
        self._running_lock = asyncio.Lock()

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

        # Delete old transactions
        result = await self.delete_old_transactions()
        if result.rowcount:
            logger.debug("🧹 Deleted %d old transactions", result.rowcount)

        await self.delete_orphan_blobs()

        # Compute and store stored objecg counts as metrics
        logger.debug("🧹 Compute and store metrics...")
        await self.compute_and_store_metrics()

    @with_session
    async def delete_old_transactions(self, /, *, session):
        """
        Remove transactions older than `old_after` days, except flagged ones. The database cascades the deletion to
        messages and tag values; their blobs are then freed by the orphan sweep.
        """

        # TODO to storage

        result = await session.execute(self.storage.transactions.delete_old(self.settings.old_after_delta))
        await session.commit()
        return result

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
