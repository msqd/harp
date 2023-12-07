from functools import cached_property

from whistle import Event, EventDispatcher

from harp import get_logger
from harp.core.models.transactions import Transaction

logger = get_logger(__name__)


EVENT_CORE_CONTROLLER = "core.controller"
EVENT_CORE_REQUEST = "core.request"
EVENT_CORE_RESPONSE = "core.response"
EVENT_CORE_STARTED = "core.startup"
EVENT_CORE_VIEW = "core.view"
EVENT_TRANSACTION_ENDED = "transaction.ended"
EVENT_TRANSACTION_STARTED = "transaction.started"
EVENT_TRANSACTION_MESSAGE = "transaction.message"


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
        self.response = response


class ViewEvent(ResponseEvent):
    def __init__(self, request, response, value):
        super().__init__(request, response)
        self._value = value

    @property
    def value(self):
        return self._value


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


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction


class TransactionMessageEvent(TransactionEvent):
    def __init__(self, transaction, message):
        super().__init__(transaction)
        self.message = message
