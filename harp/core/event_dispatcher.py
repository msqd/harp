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

    def __init__(self):
        super().__init__()
        self.level = 0

    async def dispatch(self, event_id, event=None):
        logger.debug(f"⚡ {event_id} ({type(event).__name__})")
        try:
            self.level += 1
            return await super().dispatch(event_id, event)
        finally:
            self.level -= 1
