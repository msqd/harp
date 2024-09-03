import asyncio
from typing import cast

from harp import get_logger
from harp.settings import USE_PROMETHEUS
from harp_apps.storage.services import SqlStorage

from ..storage.models.base import with_session
from ..storage.types import IBlobStorage, IStorage
from .settings import OLD_AFTER, PERIOD

logger = get_logger(__name__)


class JanitorWorker:
    def __init__(self, storage: IStorage, blob_storage: IBlobStorage):
        self.storage: SqlStorage = cast(SqlStorage, storage)
        self.blob_storage: IBlobStorage = blob_storage

        self.running = False
        self.session_factory = self.storage.session_factory
        self._running_lock = asyncio.Lock()

        if USE_PROMETHEUS:
            from prometheus_client import Gauge

            self._prometheus = {
                "storage.transactions": Gauge("storage_transactions", "Transactions currently in storage."),
                "storage.messages": Gauge("storage_messages", "Messages currently in storage."),
                "storage.blobs": Gauge("storage_blobs", "Blob objects currently in storage."),
                "storage.blobs.orphans": Gauge("storage_blobs_orphans", "Orphan blobs currently in storage."),
            }

    def stop(self):
        """
        Mark the loop for termination.
        """
        self.running = False

    async def run(self):
        """
        Once dependencies are ready, start the main loop (basically, run the `loop()` every PERIOD seconds), until
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
                await asyncio.sleep(PERIOD)

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
        Remove transactions older than OLD_AFTER days. On correct database implementations (postgresql for example), it
        will cascade to related objects. On sqlite, there will be garbage left, but it's not a big deal.
        """

        # TODO to storage

        result = await session.execute(self.storage.transactions.delete_old(OLD_AFTER))
        await session.commit()
        return result

    @with_session
    async def delete_orphan_blobs(self, /, *, session):
        """
        Find and remove blobs that are not referenced anymore by any transaction.
        """

        count = None

        if self.blob_storage.type == "sql":
            result = await session.execute(self.storage.blobs.delete_orphans())
            await session.commit()
            count = result.rowcount if result.rowcount else 0
        elif self.blob_storage.type == "redis":
            pass
        else:
            pass

        if count is None:
            # The blob storage may need to clean orphans but no implementation is available
            logger.debug("🧹 DeleteOrphanBlobs[%s] Not implemented.", self.blob_storage.type)
        elif count is False:
            # The blob storage does not NEED to delete orphans (for example for a NullBlobStorage)
            pass
        else:
            logger.debug(
                "🧹 DeleteOrphanBlobs[%s] Removed %d blobs.",
                self.blob_storage.type,
                count,
            )

    @with_session
    async def compute_and_store_metrics(self, /, *, session):
        """
        Compute counts of objects in storage, and store them as metrics.
        """

        # TODO to storage

        await self.storage.metrics.insert_values(await self.compute_metrics(session))

    async def compute_metrics(self, session):
        values = {
            "storage.transactions": await self.do_count(session, "transactions"),
            "storage.messages": await self.do_count(session, "messages"),
            "storage.blobs": await self.do_count(session, "blobs"),
            "storage.blobs.orphans": await self.do_count(session, "blobs", method="count_orphans"),
        }

        if USE_PROMETHEUS:
            for key, value in values.items():
                self._prometheus[key].set(value)

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
