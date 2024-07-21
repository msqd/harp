from functools import cached_property
from typing import Optional

from httpx import Request, Response
from whistle import Event

from harp import get_logger

logger = get_logger(__name__)


class HttpClientFilterEvent(Event):
    def __init__(self, request: Request, response: Optional[Response] = None):
        self.request = request
        self.response = response

    def set_response(self, response: Response):
        self.response = response

    @property
    def endpoint(self):
        return self.request.extensions.get("harp", {}).get("endpoint", "unknown")

    @property
    def fingerprint(self):
        return f"{self.request.method} {self.request.url.raw_path.decode()}"

    @property
    def criteria(self):
        return self.endpoint, self.fingerprint, "on_remote_" + self.name.rsplit(".", 1)[-1]

    @cached_property
    def globals(self):
        return {"Response": Response, "logger": logger}

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


EVENT_FILTER_HTTP_CLIENT_REQUEST = "http_client.filter.request"
EVENT_FILTER_HTTP_CLIENT_RESPONSE = "http_client.filter.response"
