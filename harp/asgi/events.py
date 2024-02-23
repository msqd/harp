from functools import cached_property

from whistle import Event

from harp.models.transactions import Transaction
from harp.typing.transactions import Message

EVENT_CORE_STARTED = "core.started"

EVENT_CORE_REQUEST = "core.request"
EVENT_CORE_CONTROLLER = "core.controller"
EVENT_CORE_VIEW = "core.view"
EVENT_CORE_RESPONSE = "core.response"


class RequestEvent(Event):
    name = EVENT_CORE_REQUEST

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
    name = EVENT_CORE_CONTROLLER

    def __init__(self, request, controller):
        super().__init__(request)
        self._controller = controller


class ResponseEvent(RequestEvent):
    name = EVENT_CORE_RESPONSE

    def __init__(self, request, response):
        super().__init__(request)
        self.response = response


class ViewEvent(ResponseEvent):
    name = EVENT_CORE_VIEW

    def __init__(self, request, response, value):
        super().__init__(request, response)
        self._value = value

    @property
    def value(self):
        return self._value


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction


class MessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: Message):
        super().__init__(transaction)
        self.message = message
