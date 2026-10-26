import asyncio

from harp import get_logger
from harp.config import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnReadyEvent, OnShutdownEvent
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.worker import JanitorWorker

logger = get_logger(__name__)

JANITOR_WORKER_TASK = "janitor.worker.task"


async def on_bind(event: OnBindEvent):
    event.container.add_singleton(JanitorWorker)


async def on_bound(event: OnBoundEvent):
    # Sweeps are declared by other applications, possibly after this one is bound: only say we schedule them.
    event.provider.get(JanitorWorker).schedule()


async def on_ready(event: OnReadyEvent):
    # Every application is bound by now, and has declared its sweeps.
    worker = event.provider.get(JanitorWorker)
    event.provider.set(JANITOR_WORKER_TASK, asyncio.create_task(worker.run()))


async def on_shutdown(event: OnShutdownEvent):
    worker = event.provider.get(JanitorWorker)
    worker.stop()
    task = event.provider.get(JANITOR_WORKER_TASK)
    task.cancel()
    # wait for it to be gone: a query still running when the storage closes its connections never comes back
    await asyncio.gather(task, return_exceptions=True)


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
    on_ready=on_ready,
    on_shutdown=on_shutdown,
    settings_type=JanitorSettings,
)
