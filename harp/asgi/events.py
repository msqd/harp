from functools import cached_property
from typing import TYPE_CHECKING, Any, Callable, Optional

from whistle import Event

from harp.http import HttpRequest

if TYPE_CHECKING:
    from harp.http import HttpResponse

#: Event fired when the ASGI Kernel receives a "lifespan" ASGI message.
EVENT_CORE_STARTED = "core.started"


class RequestEvent(Event):
    """
    Request-aware event, that can resolve a controller from a request.
    """

    name = "core.request"

    def __init__(self, request: HttpRequest):
        self._request = request
        self._controller = None

    @cached_property
    def request(self) -> HttpRequest:
        return self._request

    @property
    def controller(self) -> Optional[Callable]:
        return self._controller

    def set_controller(self, controller: Optional[Callable]):
        self._controller = controller


#: Event fired when the ASGI Kernel receives an HTTP request, before it's processed.
EVENT_CORE_REQUEST = RequestEvent.name


class ControllerEvent(RequestEvent):
    """
    Controller and request aware event, for controller filters (e.g. decorators...).
    """

    name = "core.controller"

    def __init__(self, request: HttpRequest, controller):
        super().__init__(request)
        self._controller = controller


#: Event fired when the ASGI Kernel has resolved a controller for a request, to allow filtering
EVENT_CORE_CONTROLLER = ControllerEvent.name


class ResponseEvent(RequestEvent):
    name = "core.response"

    def __init__(self, request: HttpRequest, response: "HttpResponse"):
        super().__init__(request)
        self.response = response


#: Event fired when the ASGI Kernel has generated a response for a request, before it's sent, allowing to filter it.
EVENT_CORE_RESPONSE = ResponseEvent.name


class ViewEvent(RequestEvent):
    """
    The view event allows to transform controller return values into response objects.
    """

    name = "core.view"

    value: Any
    response: Optional["HttpResponse"]

    def __init__(self, request: HttpRequest, value: Any):
        super().__init__(request)

        self.value = value
        self.response = None

    def set_response(self, response: "HttpResponse"):
        self.response = response
        self.stop_propagation()


#: Event fired when the ASGI Kernel has called the resolved controller but got a non-HttpResponse return value, to allow
#: transforming it into a response.
EVENT_CORE_VIEW = ViewEvent.name
