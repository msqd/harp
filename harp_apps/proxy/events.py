from typing import Callable, Optional, Self

from whistle import Event

from harp import get_logger
from harp.utils.types import typeof
from harp.http.utils import normalize_path
from harp.http import BaseHttpMessage, HttpError, HttpResponse
from harp.http.requests import HttpRequest
from harp.models import Transaction
from harp.unit_of_work import auditable, loggable
from harp.unit_of_work.audit import AuditableEvent
from harp.views.json import serialize
from harp_apps.proxy.constants import CHECKING, DOWN, UP

logger = get_logger(__name__)

#: Event fired when a transaction is created.
EVENT_TRANSACTION_STARTED = "proxy.transaction.started"

#: Event fired when a message is sent to a transaction (either request or response).
EVENT_TRANSACTION_MESSAGE = "proxy.transaction.message"

#: Event fired when a transaction is finished, once the response body has been streamed to the caller.
EVENT_TRANSACTION_ENDED = "proxy.transaction.ended"

#: Event fired when an incoming request is ready to be filtered, for example by the rules application.
EVENT_FILTER_PROXY_REQUEST = "proxy.filter.request"

#: Event fired when an outgoing response is ready to be filtered, for example by the rules application.
EVENT_FILTER_PROXY_RESPONSE = "proxy.filter.response"

#: An error happened.
EVENT_PROXY_ERROR = "proxy.error"


class ProxyFilterEvent(Event):
    def __init__(
        self,
        endpoint: str,
        /,
        *,
        request: HttpRequest,
        response: Optional[HttpResponse] = None,
        transaction: Optional[Transaction] = None,
    ):
        self.endpoint = endpoint
        self.request = request
        self.response = response
        self.transaction = transaction

    def set_response(self, response: HttpResponse):
        if response is not None and not isinstance(response, HttpResponse):
            raise ValueError(f"Response must be an instance of HttpResponse, got {response!r} ({typeof(response)}).")
        self.response = response

    def _get_rule_name(self) -> str | None:
        if not self.name:
            return None
        return "on_" + self.name.rsplit(".", 1)[-1]

    @property
    def fingerprint(self):
        """``<METHOD> <path>``, with the path the proxy forwards (see :func:`normalize_path`), no query string."""
        return f"{self.request.method} {normalize_path(self.request.path)}"

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
            "transaction": self.transaction,
        }

    def execute_script(self, script: Callable):
        context = self.create_execution_context()
        script(context)
        return self.apply_script_context(context)

    def apply_script_context(self, context: dict):
        """Take into account what a script left in its execution context."""
        if context["response"] != self.response:
            if context["response"] is None:
                self.set_response(None)
            else:
                self.update(context["response"])
        return context

    def update(self, mixed: Optional[dict | HttpResponse | Self]) -> Self:
        if mixed is None:
            return self

        if isinstance(mixed, ProxyFilterEvent):
            return mixed

        if isinstance(mixed, dict):
            mixed = HttpResponse(serialize(mixed), content_type="application/json")

        if not isinstance(mixed, HttpResponse):
            raise ValueError(
                f"Response must be an instance of HttpResponse or a dict, got {mixed!r} ({typeof(mixed)})."
            )

        self.set_response(mixed)
        return self


class TransactionEvent(Event):
    def __init__(self, transaction: Transaction):
        self.transaction = transaction


class HttpMessageEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, message: BaseHttpMessage, *, max_body_size: Optional[int] = None):
        super().__init__(transaction)
        self.message = message
        #: How many bytes of the body recorders should keep, ``None`` for all of it.
        self.max_body_size = max_body_size


class ProxyErrorEvent(TransactionEvent):
    def __init__(self, transaction: Transaction, error: HttpError):
        super().__init__(transaction)
        self.error = error


#: A remote endpoint changed state: by hand (auditable, an Editor is the actor) or on its own (loggable, no actor).
EVENT_REMOTE_STATE_CHANGED = "proxy.remote.state_changed"

_STATE_NAMES = {UP: "up", DOWN: "down", CHECKING: "checking"}


def state_name(status: int) -> str:
    """The name of a remote endpoint status, as events carry it: ``up``, ``down`` or ``checking``."""
    return _STATE_NAMES[status]


@loggable(EVENT_REMOTE_STATE_CHANGED)
class RemoteStateChanged(Event):
    """The breaker or the liveness changed the state of a remote endpoint. No actor, never an audit row."""

    details_fields = ("endpoint", "url", "from", "to")

    def __init__(self, *, endpoint: str, url: str, old: int, new: int):
        super().__init__()
        self.outcome = "succeeded"
        self.details = {"endpoint": endpoint, "url": url, "from": state_name(old), "to": state_name(new)}


@auditable(EVENT_REMOTE_STATE_CHANGED)
class RemoteStateChangedByHand(AuditableEvent):
    """An Editor set the state of a remote endpoint (or tried to: ``denied`` carries the ``required_role``)."""

    details_fields = ("endpoint", "url", "from", "to", "required_role")
