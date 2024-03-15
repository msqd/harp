from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional

from whistle import Event

from harp.http import BaseMessage, HttpRequest
from harp.models.transactions import Transaction

if TYPE_CHECKING:
    from harp.http import HttpResponse

EVENT_CORE_STARTED = "core.started"


class RequestEvent(Event):
    name = "core.request"

    def __init__(self, request: HttpRequest):
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


EVENT_CORE_REQUEST = RequestEvent.name


class ControllerEvent(RequestEvent):
    name = "core.controller"

    def __init__(self, request: HttpRequest, controller):
        super().__init__(request)
        self._controller = controller


EVENT_CORE_CONTROLLER = ControllerEvent.name


class ResponseEvent(RequestEvent):
    name = "core.response"

    def __init__(self, request: HttpRequest, response):
        super().__init__(request)
        self.response = response


EVENT_CORE_RESPONSE = ResponseEvent.name


class ControllerViewEvent(RequestEvent):
    """
    The view event allows to transform controller return values into response objects.
    """

    name = "controller.view"

    value: Any
    response: Optional["HttpResponse"]

    def __init__(self, request: HttpRequest, value: Any):
        super().__init__(request)

        self.value = value
        self.response = None

    def set_response(self, response: "HttpResponse"):
        self.response = response
        self.stop_propagation()


EVENT_CONTROLLER_VIEW = ControllerViewEvent.name


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction


class MessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: BaseMessage):
        super().__init__(transaction)
        self.message = message
