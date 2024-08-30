from typing import Optional

from whistle import AsyncEventDispatcher, IDispatchedEvent, IEvent, IListener

from harp import get_logger

__title__ = "Event Dispatcher"


class LoggingAsyncEventDispatcher(AsyncEventDispatcher):
    """
    Adds logging to AsyncEventDispatcher, should probably go into whistle 2.x (with a bit of reengineering).

    todo: pass logger or logger name to constructor, choose logging level
    todo: add check for non-coroutines listeners which is wrong but leads to an undecypherable error message
    """

    def __init__(self, *, logger=None):
        self.logger = logger or get_logger(__name__)
        super().__init__()

    def add_listener(self, event_id: str, listener: IListener, /, *, priority: int = 0):
        self.logger.debug(f"👂 [Add] {event_id} ({listener})")
        super().add_listener(event_id, listener, priority=priority)

    async def adispatch(self, event_id: str, event: Optional[IEvent] = None, /) -> IDispatchedEvent:
        self.logger.info(f"⚡️ [Dispatch] {event_id} ({type(event).__name__})")
        try:
            return await super().adispatch(event_id, event)
        except Exception as e:
            self.logger.error(f"⚡️ [Error] {event_id} ({type(event).__name__}) failed: {e}")
            raise

    async def _adispatch(self, listeners, event):
        for listener in listeners:
            self.logger.debug(f"⚡️ [DispatchOne] listener: {listener}")
            await listener(event)
            if event.propagation_stopped:
                break
