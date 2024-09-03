from datetime import UTC, datetime
from functools import cached_property, lru_cache
from typing import Optional, cast
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from httpx import AsyncClient, codes
from pyheck import shouty_snake
from whistle import IAsyncEventDispatcher

from harp import __parsed_version__, get_logger
from harp.http import BaseHttpMessage, HttpError, HttpRequest, HttpResponse
from harp.http.utils import parse_cache_control
from harp.models import Transaction
from harp.settings import USE_PROMETHEUS
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.performances import performances_observer
from harp.utils.tpdex import tpdex

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
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    ProxyFilterEvent,
    TransactionEvent,
)
from .helpers import extract_tags_from_request
from .settings.remote import Remote

logger = get_logger(__name__)

_prometheus = None
if USE_PROMETHEUS:
    from prometheus_client import Counter, Histogram

    _prometheus = {
        "call": Counter("proxy_calls", "Requests to the proxy.", ["name", "method"]),
        "time.full": Histogram(
            "proxy_time_full",
            "Requests to the proxy including overhead.",
            ["name", "method"],
        ),
        "time.forward": Histogram("proxy_time_forward", "Forward time.", ["name", "method"]),
    }


class HttpProxyController:
    name: Optional[str] = None
    """Controller name, also refered as endpoint name (for example in
    :class:`Transaction <harp.models.Transaction>`)."""

    user_agent: Optional[str] = None
    """User agent to use when proxying requests (will default to harp/<version>)."""

    _dispatcher: Optional[IAsyncEventDispatcher] = None
    """Event dispatcher for this controller."""

    remote: Remote
    """Base URL to proxy requests to."""

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
        self.http_client = http_client
        self.remote = remote
        if not isinstance(remote, Remote):
            raise TypeError(f"Expected Remote, got {type(remote).__name__}.")
        self.name = name or self.name
        self._logging = logging
        self._dispatcher = dispatcher or self._dispatcher

        # we only expose minimal information about the exact version
        if not self.user_agent:
            try:
                self.user_agent = f"harp/{__parsed_version__.major}.{__parsed_version__.minor}"
            except AttributeError:
                self.user_agent = "harp"

    async def adispatch(self, event_id, event=None):
        """
        Shortcut method to dispatch an event using the controller's dispatcher, if there is one.

        :return: :class:`IEvent <whistle.IEvent>` or None
        """
        if self._dispatcher:
            return await self._dispatcher.adispatch(event_id, event)

    def debug(self, message, *args, **kwargs):
        if not self._logging:
            return
        transaction: Transaction | None = kwargs.pop("transaction", None)
        if transaction:
            kwargs["transaction"] = transaction.id
            kwargs.update(transaction.extras)
        logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        if not self._logging:
            return
        transaction: Transaction | None = kwargs.pop("transaction", None)
        if transaction:
            kwargs["transaction"] = transaction.id
            kwargs.update(transaction.extras)
        logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        if not self._logging:
            return
        transaction: Transaction | None = kwargs.pop("transaction", None)
        if transaction:
            kwargs["transaction"] = transaction.id
            kwargs.update(transaction.extras)
        logger.warning(message, *args, **kwargs)

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        """Handle an incoming request and proxy it to the configured URL."""

        labels = {"name": self.name or "-", "method": request.method}

        with performances_observer("harp_proxy", labels=labels):
            # create an envelope to override things, without touching the original request
            context = ProxyFilterEvent(self.name, request=request)

            await self.adispatch(EVENT_FILTER_PROXY_REQUEST, context)

            remote_err = None
            try:
                remote_url = self.remote.get_url()
            except IndexError as exc:
                remote_url = None
                remote_err = exc
            parsed_remote_url = urlparse(remote_url) if remote_url else None

            # override a few required headers. That may be done in the httpx request instead of here.
            # And that would remove the need for WrappedHttpRequest? Maybe not because of our custom filters.
            if parsed_remote_url:
                context.request.headers["host"] = parsed_remote_url.netloc
            if self.user_agent:
                context.request.headers["user-agent"] = self.user_agent

            # create transaction (shouldn't that be before the filter operation ? it's debatable.)
            transaction = await self._create_transaction_from_request(
                context.request, tags=extract_tags_from_request(context.request)
            )
            if not remote_url:
                transaction.extras["status_class"] = "ERR"
                return await self.end_transaction(
                    remote_url,
                    transaction,
                    HttpError(
                        "Unavailable",
                        exception=remote_err,
                        verbose_message="Service Unavailable (no remote endpoint available)",
                        status=ERR_UNAVAILABLE_STATUS_CODE,
                    ),
                )

            await context.request.aread()
            url = urljoin(remote_url, context.request.path) + (
                f"?{urlencode(context.request.query)}" if context.request.query else ""
            )

            with performances_observer("harp_http", labels=labels):
                if not context.response:
                    # PROXY REQUEST
                    remote_request: httpx.Request = self.http_client.build_request(
                        context.request.method,
                        url,
                        headers=list(context.request.headers.items()),
                        content=context.request.body,
                        extensions={"harp": {"endpoint": self.name}},
                    )
                    context.request.extensions["remote_method"] = remote_request.method
                    context.request.extensions["remote_url"] = remote_request.url

                    self.debug(
                        f"▶▶ {context.request.method} {url}",
                        transaction=transaction,
                        extensions=remote_request.extensions,
                    )

                    # PROXY RESPONSE
                    try:
                        remote_response: httpx.Response = await self.http_client.send(remote_request)
                    except Exception as exc:
                        return await self.end_transaction(remote_url, transaction, exc)

                    self.remote.notify_url_status(remote_url, remote_response.status_code)

                    await remote_response.aread()
                    await remote_response.aclose()

                    if self.remote[remote_url].status == CHECKING and 200 <= remote_response.status_code < 400:
                        self.remote.set_up(remote_url)

                    try:
                        _elapsed = f"{remote_response.elapsed.total_seconds()}s"
                    except RuntimeError:
                        _elapsed = "n/a"
                    self.debug(
                        f"◀◀ {remote_response.status_code} {remote_response.reason_phrase} ({_elapsed}{' cached' if remote_response.extensions.get('from_cache') else ''})",
                        transaction=transaction,
                    )

                    response_headers = {
                        k: v
                        for k, v in remote_response.headers.multi_items()
                        if k.lower() not in ("server", "date", "content-encoding", "content-length")
                    }
                    # XXX for now, we use transaction "extras" to store searchable data for later
                    transaction.extras["status_class"] = f"{remote_response.status_code // 100}xx"

                    if remote_response.extensions.get("from_cache"):
                        transaction.extras["cached"] = remote_response.extensions.get("cache_metadata", {}).get(
                            "cache_key", True
                        )

                    context.response = HttpResponse(
                        remote_response.content, status=remote_response.status_code, headers=response_headers
                    )
            await self.adispatch(EVENT_FILTER_PROXY_RESPONSE, context)

            await context.response.aread()

            return await self.end_transaction(remote_url, transaction, context.response)

    async def end_transaction(
        self,
        remote_url: Optional[str],
        transaction: Transaction,
        response: BaseHttpMessage | Exception,
    ):
        spent = int((datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 100000) / 100
        transaction.finished_at = datetime.now(UTC)
        transaction.elapsed = spent

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
                if self.remote[remote_url].failure(error_name):
                    self.remote.refresh()

        if isinstance(response, HttpError):
            transaction.extras["status_class"] = "ERR"
            self.warning(
                f"◀ {type(response).__name__} {response.message} ({spent}ms)",
                transaction=transaction,
            )
        elif isinstance(response, HttpResponse):
            reason = codes.get_reason_phrase(response.status)
            self.info(f"◀ {response.status} {reason} ({spent}ms)", transaction=transaction)
        else:
            raise ValueError(f"Invalid final message type: {type(response)}")

        if transaction.extras.get("status_class") == "ERR":
            transaction.tpdex = 0
        else:
            transaction.tpdex = tpdex(transaction.elapsed)

        # dispatch message event for response
        # TODO delay after response is sent ?
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, response))
        # dispatch transaction ended event
        # TODO delay after response is sent ?
        await self.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction))

        if isinstance(response, HttpError):
            return HttpResponse(
                response.verbose_message,
                status=response.status,
                content_type="text/plain",
                extensions={"reason_phrase": response.verbose_message},
            )

        return cast(HttpResponse, response)

    async def _create_transaction_from_request(self, request: HttpRequest, *, tags=None):
        transaction = Transaction(
            id=generate_transaction_id_ksuid(),
            type="http",
            started_at=datetime.now(UTC),
            endpoint=self.name,
            tags=tags,
        )
        request.extensions["transaction"] = transaction

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

    def __repr__(self):
        return f"{type(self).__name__}({self.remote!r}, name={self.name!r})"


@lru_cache
def _get_base_network_error_type(exc_type):
    for _type in NETWORK_ERRORS:
        if issubclass(exc_type, _type):
            return _type
