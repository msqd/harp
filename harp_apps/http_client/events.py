from typing import Callable, Optional

from httpx import Request, Response
from whistle import Event

from harp import get_logger

logger = get_logger(__name__)


#: Event fired when an external request is about to be sent by the HTTP client.
EVENT_FILTER_HTTP_CLIENT_REQUEST = "http_client.filter.request"

#: Event fired when an external response is received by the HTTP client.
EVENT_FILTER_HTTP_CLIENT_RESPONSE = "http_client.filter.response"


class HttpClientFilterEvent(Event):
    """
    Custom event class embedding an :class:`httpx.Request` and an optional :class:`httpx.Response`, allowing to filter
    external requests made by the client. It also allows script execution, providing some context for systems like
    filtering rules (see ``rules`` application).

    """

    def __init__(self, request: Request, response: Optional[Response] = None):
        self.request = request
        self.response = response

    def set_response(self, response: Response):
        if response is not None and not isinstance(response, Response):
            raise ValueError(
                f"Response must be an instance of httpx.Response, got {response!r} ({type(response).__module__}.{type(response).__qualname__})."
            )
        self.response = response

    @property
    def endpoint(self):
        return self.request.extensions.get("harp", {}).get("endpoint", "unknown")

    @property
    def fingerprint(self):
        return f"{self.request.method} {self.request.url.raw_path.decode()}"

    def _get_rule_name(self) -> str | None:
        if not self.name:
            return None
        return "on_remote_" + self.name.rsplit(".", 1)[-1]

    @property
    def criteria(self):
        return self.endpoint, self.fingerprint, self._get_rule_name()

    def create_execution_context(self):
        return {
            "logger": logger,
            "rule": self._get_rule_name(),
            "endpoint": self.endpoint,
            "request": self.request,
            "response": self.response,
            "stop_propagation": self.stop_propagation,
        }

    def execute_script(self, script: Callable):
        context = self.create_execution_context()
        script(context)
        if context["response"] != self.response:
            if context["response"] is not None:
                if not isinstance(context["response"], Response):
                    raise ValueError(
                        f"Response must be an instance of httpx.Response, got {context['response']!r} ({type(context['response']).__module__}.{type(context['response']).__qualname__})."
                    )
            self.set_response(context["response"])
        return context
