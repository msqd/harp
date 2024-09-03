import asyncio
from inspect import iscoroutinefunction

from harp import get_logger
from harp.settings import USE_PROMETHEUS

logger = get_logger(__name__)


AsyncWorkerQueueBacklog = None
if USE_PROMETHEUS:
    from prometheus_client import Gauge

    AsyncWorkerQueueBacklog = Gauge(
        "async_worker_queue_backlog",
        "Number of items in the async worker queue.",
        ["queue_id"],
    )


class AsyncWorkerQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self.cleanup()
        self._task = asyncio.create_task(self())
        self._running = True

    async def __call__(self):
        while True:
            if self._last_cleanup_at < asyncio.get_event_loop().time() - 5:
                self.cleanup()

            try:
                item, ignore_errors = await self._queue.get()
            except RuntimeError:
                # queue is closed
                break
            try:
                await item()
            except Exception as e:
                if not ignore_errors:
                    logger.exception(f"Error while executing queued task: {e}")
            finally:
                self._queue.task_done()

    def cleanup(self):
        self._last_cleanup_at = asyncio.get_event_loop().time()
        self._pressure = self._queue.qsize()
        if AsyncWorkerQueueBacklog:
            # prom ignore 0 values so we set the minimum as 1
            AsyncWorkerQueueBacklog.labels(id(self)).set(max(self._pressure, 1))

    async def push(self, item, /, *, ignore_errors=False):
        if not self._running:
            raise RuntimeError("Queue is closed.")
        if not iscoroutinefunction(item):
            raise ValueError(f"Unknown item type: {type(item)}, expecting coroutine function.")

        await self._queue.put((item, ignore_errors))

    async def wait_until_empty(self):
        await self._queue.join()

    async def close(self):
        self._running = False
        await self.wait_until_empty()


def is_event_loop_running() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False
