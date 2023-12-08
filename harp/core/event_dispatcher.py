from whistle import Event, EventDispatcher

from harp import get_logger

logger = get_logger(__name__)


class AsyncEventDispatcher(EventDispatcher):
    """
    Adapts whiste's EventDispatcher to be async. Probably should go into whistle 2.x?
    """

    async def do_dispatch(self, listeners, event):
        for listener in listeners:
            await listener(event)
            if event.propagation_stopped:
                break

    async def dispatch(self, event_id, event=None):
        if event is None:
            event = Event()

        event.dispatcher = self
        event.name = event_id

        if event_id not in self._listeners:
            return event

        await self.do_dispatch(self.get_listeners(event_id), event)

        return event


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
