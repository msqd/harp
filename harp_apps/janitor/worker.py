import asyncio
from typing import cast

from harp import get_logger
from harp.typing import Storage
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage

from ..sqlalchemy_storage.models.base import with_session
from .settings import OLD_AFTER, PERIOD

logger = get_logger(__name__)


class JanitorWorker:
    def __init__(self, storage: Storage):
        self.storage: SqlAlchemyStorage = cast(SqlAlchemyStorage, storage)
        self.running = False
        self.session_factory = self.storage.session_factory

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
        await self.storage.ready()

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

        # Delete orphan blobs
        result = await self.delete_orphan_blobs()
        if result.rowcount:
            logger.debug("🧹 Deleted %d orphan blobs", result.rowcount)

        # Compute and store stored objecg counts as metrics
        logger.debug("🧹 Compute and store metrics...")
        await self.compute_and_store_metrics()

    @with_session
    async def delete_old_transactions(self, /, *, session):
        """
        Remove transactions older than OLD_AFTER days. On correct database implementations (postgresql for example), it
        will cascade to related objects. On sqlite, there will be garbage left, but it's not a big deal.
        """
        result = await session.execute(self.storage.transactions.delete_old(OLD_AFTER))
        await session.commit()
        return result

    @with_session
    async def delete_orphan_blobs(self, /, *, session):
        """
        Find and remove blobs that are not referenced anymore by any transaction.
        """
        result = await session.execute(self.storage.blobs.delete_orphans())
        await session.commit()
        return result

    @with_session
    async def compute_and_store_metrics(self, /, *, session):
        """
        Compute counts of objects in storage, and store them as metrics.
        """
        await self.storage.metrics.insert_values(await self.compute_metrics(session))

    async def compute_metrics(self, session):
        return {
            "storage.transactions": await self.do_count(session, "transactions"),
            "storage.messages": await self.do_count(session, "messages"),
            "storage.blobs": await self.do_count(session, "blobs"),
            "storage.blobs.orphans": await self.do_count(session, "blobs", method="count_orphans"),
        }

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
