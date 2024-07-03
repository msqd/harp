import asyncio
from inspect import iscoroutinefunction

from harp import get_logger

logger = get_logger(__name__)


class AsyncWorkerQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
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
