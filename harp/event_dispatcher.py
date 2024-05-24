from typing import Optional

from whistle import AsyncEventDispatcher, IDispatchedEvent, IEvent, IListener

from harp import get_logger

logger = get_logger(__name__)
__title__ = "Event Dispatcher"


class LoggingAsyncEventDispatcher(AsyncEventDispatcher):
    """
    Adds logging to AsyncEventDispatcher, should probably go into whistle 2.x (with a bit of reengineering).

    todo: pass logger or logger name to constructor, choose logging level
    todo: add check for non-coroutines listeners which is wrong but leads to an undecypherable error message
    """

    def add_listener(self, event_id: str, listener: IListener, /, *, priority: int = 0):
        logger.info(f"👂 [Add] {event_id} ({listener})")
        super().add_listener(event_id, listener, priority=priority)

    async def adispatch(self, event_id: str, event: Optional[IEvent] = None, /) -> IDispatchedEvent:
        logger.info(f"⚡ [Dispatch] {event_id} ({type(event).__name__})")
        try:
            return await super().adispatch(event_id, event)
        except Exception as e:
            logger.error(f"⚡ [Error] {event_id} ({type(event).__name__}) failed: {e}")
            raise

    async def _adispatch(self, listeners, event):
        for listener in listeners:
            logger.debug(f"⚡ [DispatchOne] listener: {listener}")
            await listener(event)
            if event.propagation_stopped:
                break
