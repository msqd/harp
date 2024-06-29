import asyncio

from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent
from harp_apps.janitor.worker import JanitorWorker


class JanitorApplication(Application):
    depends_on = {"storage"}

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(JanitorWorker)

    async def on_bound(self, event: FactoryBoundEvent):
        self.task = asyncio.create_task(
            event.provider.get(JanitorWorker).run(),
        )

    async def on_dispose(self, event: FactoryDisposeEvent):
        await event.provider.get(JanitorWorker).finalize()
        await self.task
