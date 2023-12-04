from functools import cached_property

from whistle import Event, EventDispatcher

from harp import get_logger

logger = get_logger(__name__)


class BaseASGIEvent(Event):
    dispatcher = None
    name = None


class RequestEvent(BaseASGIEvent):
    def __init__(self, request):
        self._request = request
        self._controller = None

    @cached_property
    def request(self):
        return self._request

    @property
    def controller(self):
        return self._controller

    def set_controller(self, controller):
        self._controller = controller


class ControllerEvent(RequestEvent):
    def __init__(self, request, controller):
        super().__init__(request)
        self._controller = controller


class ResponseEvent(RequestEvent):
    def __init__(self, request, response):
        super().__init__(request)
        self._response = response

    @property
    def response(self):
        return self._response


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
    async def dispatch(self, event_id, event=None):
        logger.info(f"⚡ {event_id} ({type(event).__name__})")
        return await super().dispatch(event_id, event)


class TransactionEvent(Event):
    def __init__(self, transaction_id):
        self.transaction_id = transaction_id


class TransactionMessageEvent(TransactionEvent):
    def __init__(self, transaction_id, kind, content):
        super().__init__(transaction_id)
        self.kind = kind
        self.content = content
