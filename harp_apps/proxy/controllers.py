from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from functools import cached_property, lru_cache
from typing import Optional, cast, override
from urllib.parse import urlencode, urljoin

from httpx import AsyncClient, codes
from pyheck import shouty_snake
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.http import BaseHttpMessage, HttpError, HttpRequest, HttpResponse
from harp.http.utils import parse_cache_control
from harp.models import Transaction
from harp.utils.api import api
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.tpdex import tpdex

from .adapters import HttpClientProxyAdapter
from .constants import (
    BREAK_ON_NETWORK_ERROR,
    BREAK_ON_UNHANDLED_EXCEPTION,
    CHECKING,
    ERR_UNAVAILABLE_STATUS_CODE,
    ERR_UNHANDLED_MESSAGE,
    ERR_UNHANDLED_STATUS_CODE,
    ERR_UNHANDLED_VERBOSE_MESSAGE,
    NETWORK_ERRORS,
)
from .events import (
    EVENT_FILTER_PROXY_REQUEST,
    EVENT_FILTER_PROXY_RESPONSE,
    EVENT_PROXY_ERROR,
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    ProxyErrorEvent,
    ProxyFilterEvent,
    TransactionEvent,
)
from .helpers import extract_tags_from_request
from .settings.remote import Remote

logger = get_logger(__name__)

# XXX: move to some type module ?
ProxyFilterResult = Optional[ProxyFilterEvent | HttpResponse | dict]


class AbstractHttpProxyController(ABC):
    name: Optional[str] = None
    """Controller name, also refered as endpoint name (for example in
    :class:`Transaction <harp.models.Transaction>`)."""

    remote: Remote
    """Base URL to proxy requests to."""

    _dispatcher: Optional[IAsyncEventDispatcher] = None
    """Event dispatcher for this controller."""

    @cached_property
    def dispatcher(self):
        """Read-only reference to the event dispatcher."""
        return self._dispatcher

    def __init__(
        self,
        remote: Remote,
        *,
        http_client: AsyncClient,
        dispatcher: Optional[IAsyncEventDispatcher] = None,
        name=None,
        logging=True,
    ):
        self.remote = remote
        if not isinstance(remote, Remote):
            raise TypeError(f"Expected Remote, got {type(remote).__name__}.")
        self.name = name or self.name
        self._logging = logging
        self._dispatcher = dispatcher or self._dispatcher

        self.proxy = HttpClientProxyAdapter(http_client, extensions={"endpoint": self.name})

        self.initialize()

    @api("0.8")
    @abstractmethod
    async def __call__(self, request: HttpRequest) -> HttpResponse:
        """Handle an incoming request, produce a response."""
        raise NotImplementedError()

    def __repr__(self):
        return f"{type(self).__name__}({self.remote!r}, name={self.name!r})"

    def initialize(self):
        pass

    async def adispatch(self, event_id, event=None):
        """
        Shortcut method to dispatch an event using the controller's dispatcher, if there is one.

        :return: :class:`IEvent <whistle.IEvent>` or None
        """
        if self._dispatcher:
            return await self._dispatcher.adispatch(event_id, event)

    def debug(self, message, *args, **kwargs):
        self._log("debug", message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._log("info", message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._log("warning", message, *args, **kwargs)

    def _log(self, level, message, *args, **kwargs):
        if not self._logging:
            return
        transaction: Transaction | None = kwargs.pop("transaction", None)
        if transaction:
            kwargs["transaction"] = transaction.id
            kwargs.update(transaction.extras)
        getattr(logger, level)(message, *args, **kwargs)


class HttpProxyController(AbstractHttpProxyController):
    """
    Adds the transaction logic and actual implementation to the abstract controller.
    """

    @api("0.8")
    async def filter_request(self, context: ProxyFilterEvent) -> ProxyFilterResult:
        return cast(
            ProxyFilterEvent,
            await self.adispatch(EVENT_FILTER_PROXY_REQUEST, context),
        )

    @api("0.8")
    async def filter_response(self, context: ProxyFilterEvent) -> ProxyFilterResult:
        return cast(
            ProxyFilterEvent,
            await self.adispatch(EVENT_FILTER_PROXY_RESPONSE, context),
        )

    @override
    async def __call__(self, request: HttpRequest) -> HttpResponse:
        base_url = None
        transaction = await self._create_transaction_from_request(request, tags=extract_tags_from_request(request))

        # create the context, an event that will be passed through the transaction lifecycle.
        # todo: embed in transaction ?
        context = ProxyFilterEvent(self.name, request=request)
        context.update(await self.filter_request(context))

        # If nothing prepared a ready to send response, it's time to forward the request.
        if not context.response:
            # do we have an available remote url? if not, we can stop there.
            try:
                base_url, full_url = await self._get_next_url_for(context)
            except IndexError as exc:
                response = HttpError(
                    "Unavailable",
                    exception=exc,
                    verbose_message="Service Unavailable (no remote endpoint available)",
                    status=ERR_UNAVAILABLE_STATUS_CODE,
                )
                return await self.failure(transaction, base_url, response)

            # todo: streaming should pass through to avoid reading all the content in memory
            await context.request.aread()

            # Attempt to forward the request to the remote server.
            try:
                self.debug(
                    f"▶▶ {context.request.method} {full_url}", transaction=transaction, extensions=request.extensions
                )
                response = await self.forward(transaction, context, base_url, full_url)
            except Exception as exc:
                return await self.failure(transaction, base_url, exc)
            context.set_response(response)

        context = await self.filter_response(context) or context

        # todo: streaming should pass through to avoid reading all the content in memory
        await context.response.aread()

        return await self.end_transaction(transaction, context.response)

    async def forward(
        self, transaction: Transaction, context: ProxyFilterEvent, base_url: str, full_url: str
    ) -> HttpResponse:
        """
        Forward the request to the remote server.

        :param transaction: The current transaction object.
        :param context: The proxy filter event context.
        :param base_url: The base URL of the remote server.
        :param full_url: The full URL to which the request is forwarded.
        :return: The HTTP response received from the remote server.
        """
        response = await self.proxy.send(context.request, full_url)

        # Update the status of the remote URL based on the response status code
        self.remote.notify_url_status(base_url, response.status_code)

        await response.aread()
        await response.aclose()

        is_response_from_cache = response.extensions.get("from_cache")

        # If the remote URL is in CHECKING status and the response is successful, set it up
        if self.remote[base_url].status == CHECKING and 200 <= response.status_code < 400:
            self.remote.set_up(base_url)

        self.debug(
            f"◀◀ {response.status_code} {response.reason_phrase} "
            f"({_format_elapsed(response.elapsed)}{' cached' if is_response_from_cache else ''})",
            transaction=transaction,
        )

        # Filter out certain headers from the response
        headers = {
            k: v
            for k, v in response.headers.multi_items()
            if k.lower() not in ("server", "date", "content-encoding", "content-length")
        }

        # Store the status class in the transaction extras for later use
        transaction.extras["status_class"] = f"{response.status_code // 100}xx"

        if is_response_from_cache:
            transaction.extras["cached"] = response.extensions.get("cache_metadata", {}).get("cache_key", True)

        return HttpResponse(response.content, status=response.status_code, headers=headers)

    async def _get_next_url_for(self, context) -> tuple[str, str]:
        base_url = self.remote.get_url()
        relative_url = context.request.path.lstrip("/")
        return base_url, urljoin(base_url, relative_url) + (
            f"?{urlencode(context.request.query)}" if context.request.query else ""
        )

    async def failure(
        self,
        transaction: Transaction,
        base_url: Optional[str],
        response: Optional[Exception | BaseHttpMessage] = None,
    ):
        """
        Handle a failure scenario by updating the transaction status and creating an appropriate HttpError response.

        :param transaction: The current transaction object.
        :param base_url: The base URL of the remote server.
        :param response: The response or exception that caused the failure.
        :return: The final HttpResponse object.
        """
        transaction.extras["status_class"] = "ERR"

        if isinstance(response, Exception):
            error_kind = BREAK_ON_UNHANDLED_EXCEPTION
            error_name = shouty_snake(type(response).__name__)

            if network_error_type := _get_base_network_error_type(type(response)):
                error_kind = BREAK_ON_NETWORK_ERROR
                _status_code, _message, _verbose_message = NETWORK_ERRORS[network_error_type]
                response = HttpError(
                    _message,
                    exception=response,
                    status=_status_code,
                    verbose_message=_verbose_message,
                )
            else:
                response = HttpError(
                    ERR_UNHANDLED_MESSAGE,
                    exception=response,
                    status=ERR_UNHANDLED_STATUS_CODE,
                    verbose_message=ERR_UNHANDLED_VERBOSE_MESSAGE,
                )

            if error_kind in self.remote.settings.break_on:
                if base_url and self.remote[base_url].failure(error_name):
                    self.remote.refresh()

            await self.adispatch(EVENT_PROXY_ERROR, ProxyErrorEvent(transaction, response))

        return await self.end_transaction(transaction, response)

    async def end_transaction(
        self,
        transaction: Transaction,
        response: BaseHttpMessage | Exception,
    ) -> HttpResponse:
        """
        Finalize the transaction and dispatch relevant events.

        :param transaction: The current transaction object.
        :param response: The response or exception that concluded the transaction.
        :return: The final HttpResponse object.
        """
        transaction.finished_at = datetime.now(UTC)
        transaction.elapsed = round((datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 1000, 2)

        if isinstance(response, HttpError):
            transaction.extras["status_class"] = "ERR"
            self.warning(
                f"◀ {type(response).__name__} {response.message} ({transaction.elapsed}ms)",
                transaction=transaction,
            )
        elif isinstance(response, HttpResponse):
            reason = codes.get_reason_phrase(response.status)
            self.info(f"◀ {response.status} {reason} ({transaction.elapsed}ms)", transaction=transaction)
        else:
            raise ValueError(f"Invalid final message type: {type(response)}")

        transaction.tpdex = 0 if transaction.extras.get("status_class") == "ERR" else tpdex(transaction.elapsed)

        # Dispatch message event for response
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, response))
        # Dispatch transaction ended event
        await self.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction))

        if isinstance(response, HttpError):
            return HttpResponse(
                response.verbose_message,
                status=response.status,
                content_type="text/plain",
                extensions={"reason_phrase": response.verbose_message},
            )

        return cast(HttpResponse, response)

    async def _create_transaction_from_request(self, request: HttpRequest, *, tags=None) -> Transaction:
        """
        Create a new transaction from the incoming request, generating a new (random, but orderable according to the
        instant it happens) transaction ID.

        Once created, it dispatches the EVENT_TRANSACTION_STARTED event to allow storage applications (or anything
        else) to react to this creation, then it dispatches the EVENT_TRANSACTION_MESSAGE event to allow to react to
        the fact this transaction contained a request.

        :return: Transaction
        """
        transaction = Transaction(
            id=generate_transaction_id_ksuid(),
            type="http",
            started_at=datetime.now(UTC),
            endpoint=self.name,
            tags=tags,
        )
        request.extensions["transaction"] = transaction

        # If the request cache control asked for cache to be disabled, mark it in transaction.
        request_cache_control = request.headers.get("cache-control")
        if request_cache_control:
            request_cache_control = parse_cache_control([request_cache_control])
            if request_cache_control.no_cache:
                transaction.extras["no_cache"] = True

        # XXX for now, we use transaction "extras" to store searchable data for later
        transaction.extras["method"] = request.method

        self.info(f"▶ {request.method} {request.path}", transaction=transaction)

        # dispatch transaction started event
        # we don't really want to await this, should run in background ? or use an async queue ?
        await self.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction))

        # dispatch message event for request
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, request))

        return transaction


@lru_cache
def _get_base_network_error_type(exc_type):
    for _type in NETWORK_ERRORS:
        if issubclass(exc_type, _type):
            return _type


def _format_elapsed(elapsed: timedelta):
    try:
        return f"{elapsed.total_seconds()}s"
    except RuntimeError:
        return "n/a"
