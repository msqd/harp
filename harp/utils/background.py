import asyncio
from inspect import iscoroutinefunction

from prometheus_client import Gauge

from harp import get_logger

logger = get_logger(__name__)


ASYNC_WORKER_QUEUE_BACKLOG_GAUGE = Gauge(
    "async_worker_queue_backlog",
    "Number of items in the async worker queue.",
    ["queue_id"],
)


class AsyncWorkerQueue:
    def __init__(self):
        #: Monotonic clock, in seconds. The event loop clock unless a test injects its own.
        self.clock = asyncio.get_running_loop().time
        self._queue = asyncio.Queue()
        self.cleanup()
        self._task = asyncio.create_task(self())
        self._running = True

    async def __call__(self):
        while True:
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
                # Measure after each job: the backlog drains without any push.
                self.cleanup()

    def cleanup(self):
        """Measures the backlog, and reports it in the ``async_worker_queue_backlog`` gauge."""
        self._backlog = self._queue.qsize()
        if ASYNC_WORKER_QUEUE_BACKLOG_GAUGE:
            ASYNC_WORKER_QUEUE_BACKLOG_GAUGE.labels(id(self)).set(self._backlog)

    async def push(self, item, /, *, ignore_errors=False):
        if not self._running:
            raise RuntimeError("Queue is closed.")
        if not iscoroutinefunction(item):
            raise ValueError(f"Unknown item type: {type(item)}, expecting coroutine function.")

        await self._queue.put((item, ignore_errors))
        # Measure on push: a stalled consumer never gets to refresh it.
        self.cleanup()

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
