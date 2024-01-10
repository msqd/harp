import asyncio
from inspect import iscoroutinefunction

from harp import get_logger

logger = get_logger(__name__)


class AsyncWorkerQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self())

    async def __call__(self):
        while True:
            item, ignore_errors = await self._queue.get()
            try:
                await item()
            except Exception as e:
                if not ignore_errors:
                    logger.exception(f"Error while executing queued task: {e}")

    async def push(self, item, /, *, ignore_errors=False):
        if not iscoroutinefunction(item):
            raise ValueError(f"Unknown item type: {type(item)}, expecting coroutine function.")

        await self._queue.put((item, ignore_errors))
