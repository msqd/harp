from typing import Callable, Optional

from whistle import Event

from harp import get_logger
from harp.http import BaseHttpMessage, HttpResponse
from harp.http.requests import HttpRequest
from harp.models import Transaction

logger = get_logger(__name__)

#: Event fired when a transaction is created.
EVENT_TRANSACTION_STARTED = "proxy.transaction.started"

#: Event fired when a message is sent to a transaction (either request or response).
EVENT_TRANSACTION_MESSAGE = "proxy.transaction.message"

#: Event fired when a transaction is finished, before the response is sent back to the caller.
EVENT_TRANSACTION_ENDED = "proxy.transaction.ended"

#: Event fired when an incoming request is ready to be filtered, for example by the rules application.
EVENT_FILTER_PROXY_REQUEST = "proxy.filter.request"

#: Event fired when an outgoing response is ready to be filtered, for example by the rules application.
EVENT_FILTER_PROXY_RESPONSE = "proxy.filter.response"


class ProxyFilterEvent(Event):
    def __init__(
        self,
        endpoint: str,
        /,
        *,
        request: HttpRequest,
        response: Optional[HttpResponse] = None,
    ):
        self.endpoint = endpoint
        self.request = request
        self.response = response

    def set_response(self, response: HttpResponse):
        if response is not None and not isinstance(response, HttpResponse):
            raise ValueError(
                f"Response must be an instance of HttpResponse, got {response!r} ({type(response).__module__}.{type(response).__qualname__})."
            )
        self.response = response

    def _get_rule_name(self) -> str | None:
        if not self.name:
            return None
        return "on_" + self.name.rsplit(".", 1)[-1]

    @property
    def criteria(self):
        return self.endpoint, str(self.request), self._get_rule_name()

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
                if not isinstance(context["response"], HttpResponse):
                    raise ValueError(
                        f"Response must be an instance of HttpResponse, got {context['response']!r} ({type(context['response']).__module__}.{type(context['response']).__qualname__})."
                    )
            self.set_response(context["response"])
        return context


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction


class HttpMessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: BaseHttpMessage):
        super().__init__(transaction)
        self.message = message
