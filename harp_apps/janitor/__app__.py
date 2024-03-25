import asyncio
from typing import cast

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent
from harp.typing import Storage
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage

logger = get_logger(__name__)


class JanitorWorker:
    def __init__(self, storage: Storage):
        self.storage: SqlAlchemyStorage = cast(SqlAlchemyStorage, storage)
        self.running = False

    def stop(self):
        self.running = False

    async def run(self):
        self.running = True
        while self.running:
            try:
                await self.loop()
            except Exception as exc:
                logger.exception(exc)
            await asyncio.sleep(60)

    async def loop(self):
        async with self.storage.session() as session:
            metrics = {
                "storage.transactions": (await session.execute(self.storage.transactions.count())).scalar(),
                "storage.messages": (await session.execute(self.storage.messages.count())).scalar(),
                "storage.blobs": (await session.execute(self.storage.blobs.count())).scalar(),
            }

            await self.storage.metrics.insert_values(metrics)


class JanitorApplication(Application):
    async def on_bind(self, event: FactoryBindEvent):
        pass

    async def on_bound(self, event: FactoryBoundEvent):
        self.worker = JanitorWorker(event.provider.get(Storage))
        self.worker_task = asyncio.create_task(self.worker.run())

    async def unmount(self):
        self.worker.stop()
