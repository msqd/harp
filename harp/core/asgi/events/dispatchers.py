from whistle import Event, EventDispatcher

from harp import get_logger

logger = get_logger(__name__)


class AsyncEventDispatcher(EventDispatcher):
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
    def __init__(self):
        super().__init__()
        self.level = 0

    async def dispatch(self, event_id, event=None):
        logger.info(f"⚡ {event_id} ({type(event).__name__})")
        try:
            self.level += 1
            return await super().dispatch(event_id, event)
        finally:
            self.level -= 1
