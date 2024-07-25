import asyncio

from harp import get_logger
from harp.config import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnShutdownEvent
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.types import IStorage

logger = get_logger(__name__)

JANITOR_WORKER_TASK = "janitor.worker.task"


async def on_bind(event: OnBindEvent):
    event.container.add_singleton(JanitorWorker)


async def on_bound(event: OnBoundEvent):
    await event.provider.get(IStorage).ready()

    worker = event.provider.get(JanitorWorker)
    event.provider.set(JANITOR_WORKER_TASK, asyncio.create_task(worker.run()))


async def on_shutdown(event: OnShutdownEvent):
    worker = event.provider.get(JanitorWorker)
    worker.stop()
    event.provider.get(JANITOR_WORKER_TASK).cancel()


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
    on_shutdown=on_shutdown,
    dependencies=["storage"],
)
