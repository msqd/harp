from typing import Optional

from whistle import AsyncEventDispatcher, IDispatchedEvent, IEvent

from harp import get_logger

logger = get_logger(__name__)


class LoggingAsyncEventDispatcher(AsyncEventDispatcher):
    """
    Adds logging to AsyncEventDispatcher, should probably go into whistle 2.x (with a bit of reengineering).

    todo: pass logger or logger name to constructor, choose logging level
    todo: add check for non oroutines listeners which is wrong but leads to an undecypherable error message
    """

    async def adispatch(self, event_id: str, event: Optional[IEvent] = None, /) -> IDispatchedEvent:
        logger.debug(f"⚡ {event_id} ({type(event).__name__})")
        try:
            return await super().adispatch(event_id, event)
        except Exception as e:
            logger.exception(f"⚡ {event_id} ({type(event).__name__}) failed: {e}")
