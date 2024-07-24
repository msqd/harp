import asyncio

from harp import get_logger
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.types import IStorage

logger = get_logger(__name__)

JANITOR_WORKER_TASK = "janitor.worker.task"


class JanitorLifecycle:
    @staticmethod
    async def on_bind(event: FactoryBindEvent):
        event.container.add_singleton(JanitorWorker)

    @staticmethod
    async def on_bound(event: FactoryBoundEvent):
        await event.provider.get(IStorage).ready()

        worker = event.provider.get(JanitorWorker)
        event.provider.set(JANITOR_WORKER_TASK, asyncio.create_task(worker.run()))

    @staticmethod
    async def on_dispose(event: FactoryDisposeEvent):
        worker = event.provider.get(JanitorWorker)
        worker.stop()
        event.provider.get(JANITOR_WORKER_TASK).cancel()
