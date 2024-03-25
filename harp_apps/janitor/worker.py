import asyncio
from typing import cast

from harp import get_logger
from harp.typing import Storage
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage

from .settings import OLD_AFTER, PERIOD

logger = get_logger(__name__)


class JanitorWorker:
    def __init__(self, storage: Storage):
        self.storage: SqlAlchemyStorage = cast(SqlAlchemyStorage, storage)
        self.running = False

    def stop(self):
        self.running = False

    async def run(self):
        # do not start before storage is ready
        await self.storage.ready()

        self.running = True
        while self.running:
            try:
                await self.loop()
            except Exception as exc:
                logger.exception(exc)
            await asyncio.sleep(PERIOD)

    async def count(self, name: str, session, method_name="count"):
        return (
            await session.execute(
                getattr(
                    getattr(self.storage, name),
                    method_name,
                )()
            )
        ).scalar()

    async def loop(self):
        async with self.storage.session() as session:
            result = await self._delete_old_transactions(session)
            await session.commit()
            if result.rowcount:
                logger.info("🧹 Deleted %d old transactions", result.rowcount)

        async with self.storage.session() as session:
            result = await self._delete_orphan_blobs(session)
            await session.commit()
            if result.rowcount:
                logger.info("🧹 Deleted %d orphan blobs", result.rowcount)

        async with self.storage.session() as session:
            logger.info("🧹 Compute and store metrics...")
            await self._compute_and_store_metrics(session)

    async def _delete_old_transactions(self, session):
        return await session.execute(self.storage.transactions.delete_old(OLD_AFTER))

    async def _delete_orphan_blobs(self, session):
        return await session.execute(self.storage.blobs.delete_orphans())

    async def _compute_and_store_metrics(self, session):
        await self.storage.metrics.insert_values(
            {
                "storage.transactions": await self.count("transactions", session),
                "storage.messages": await self.count("messages", session),
                "storage.blobs": await self.count("blobs", session),
                "storage.blobs.orphans": await self.count("blobs", session, "count_orphans"),
            }
        )
