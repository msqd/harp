from whistle import Event
from whistle.dispatcher import AsyncEventDispatcher

from harp import get_logger

logger = get_logger(__name__)


class BaseEvent(Event):
    dispatcher = None
    name = None


class LoggingAsyncEventDispatcher(AsyncEventDispatcher):
    """
    Adds logging to AsyncEventDispatcher, should probably go into whistle 2.x (with a bit of reengineering).

    todo: pass logger or logger name to constructor, choose logging level
    """

    async def dispatch(self, event_id, event=None):
        logger.debug(f"⚡ {event_id} ({type(event).__name__})")
        try:
            return await super().dispatch(event_id, event)
        except Exception as e:
            logger.exception(f"⚡ {event_id} ({type(event).__name__}) failed: {e}")
