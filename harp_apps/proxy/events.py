from functools import cached_property
from typing import Optional

from whistle import Event

from harp import get_logger
from harp.http import HttpResponse
from harp.http.requests import HttpRequest

logger = get_logger(__name__)

EVENT_TRANSACTION_STARTED = "proxy.transaction.started"
EVENT_TRANSACTION_MESSAGE = "proxy.transaction.message"
EVENT_TRANSACTION_ENDED = "proxy.transaction.ended"
EVENT_FILTER_REQUEST = "proxy.filter.request"
EVENT_FILTER_RESPONSE = "proxy.filter.response"


class ProxyFilterEvent(Event):
    def __init__(self, endpoint: str, /, *, request: HttpRequest, response: Optional[HttpResponse] = None):
        self.endpoint = endpoint
        self.request = request
        self.response = response

    def set_response(self, response: HttpResponse):
        if not isinstance(response, HttpResponse):
            raise ValueError(
                f"Response must be an instance of HttpResponse, got {response!r} ({type(response).__module__}.{type(response).__qualname__})."
            )
        self.response = response

    @property
    def criteria(self):
        return self.endpoint, str(self.request), "on_" + self.name.rsplit(".", 1)[-1]

    @cached_property
    def globals(self):
        return {"logger": logger}

    @property
    def locals(self):
        return {
            "event": self,
            "endpoint": self.endpoint,
            "request": self.request,
            "response": self.response,
            "set_response": self.set_response,
            "stop_propagation": self.stop_propagation,
        }
