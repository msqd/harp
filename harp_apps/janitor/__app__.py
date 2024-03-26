import asyncio

from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent
from harp.typing import Storage
from harp_apps.janitor.worker import JanitorWorker


class JanitorApplication(Application):
    async def on_bind(self, event: FactoryBindEvent):
        pass

    async def on_bound(self, event: FactoryBoundEvent):
        self.worker = JanitorWorker(event.provider.get(Storage))
        self.worker_task = asyncio.create_task(self.worker.run())

    async def unmount(self):
        self.worker.stop()
