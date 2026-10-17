import re
import unicodedata
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from functools import cached_property, lru_cache
from time import time
from httpx import AsyncClient, codes
from pyheck import shouty_snake
from typing import Optional, cast, override
from urllib.parse import unquote_to_bytes, urlencode, urlsplit
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.http import BaseHttpMessage, HttpError, HttpRequest, HttpResponse, RejectedRequest
from harp.http.utils import HOP_BY_HOP_HEADERS, hop_by_hop_names, parse_cache_control
from harp.models import Transaction
from harp.utils.api import api
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.tpdex import tpdex
from .adapters import HttpClientProxyAdapter, strip_credentials
from .constants import (
    BREAK_ON_NETWORK_ERROR,
    BREAK_ON_UNHANDLED_EXCEPTION,
    CHECKING,
    ERR_BAD_REQUEST_MESSAGE,
    ERR_BAD_REQUEST_STATUS_CODE,
    ERR_BAD_REQUEST_VERBOSE_MESSAGE,
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


MAX_FORWARDED_URL_LENGTH = 65_536
"""Longest URL httpx accepts; anything longer is refused before it gets there."""


class ProxyRoutingError(Exception):
    """Raised when an incoming request path would route the proxy off its configured upstream origin."""


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
        context = await self.start_transaction(request, tags=extract_tags_from_request(request))

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
                return await self.failure(context.transaction, base_url, response)
            except ProxyRoutingError as exc:
                response = HttpError(
                    ERR_BAD_REQUEST_MESSAGE,
                    exception=exc,
                    verbose_message=ERR_BAD_REQUEST_VERBOSE_MESSAGE,
                    status=ERR_BAD_REQUEST_STATUS_CODE,
                )
                return await self.failure(context.transaction, base_url, response)
            except RejectedRequest as exc:
                response = HttpError(exc.message, exception=exc, status=exc.status)
                return await self.failure(context.transaction, base_url, response)

            # todo: streaming should pass through to avoid reading all the content in memory
            await context.request.aread()

            # Attempt to forward the request to the remote server.
            try:
                self.debug(
                    f"▶▶ {context.request.method} {strip_credentials(full_url)}",
                    transaction=context.transaction,
                    extensions=request.extensions,
                )
                response = await self.forward(context.transaction, context, base_url, full_url)
            except Exception as exc:
                return await self.failure(context.transaction, base_url, exc)
            context.set_response(response)

        context = await self.filter_response(context) or context

        # todo: streaming should pass through to avoid reading all the content in memory
        await context.response.aread()

        return await self.end_transaction(context.transaction, context.response)

    async def forward(
        self,
        transaction: Transaction,
        context: ProxyFilterEvent,
        base_url: str,
        full_url: str,
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

        # Our cache answers this in the response extensions, and the adapter copies that answer into
        # `X-Cache` for the client's benefit. Reading the header back here instead would take the
        # answer from a public channel: an upstream behind a CDN sets `X-Cache` for its own cache
        # (CloudFront, Fastly and Varnish all do), and its hit would be recorded as ours.
        is_response_from_cache = bool(response.extensions.get("hishel_from_cache"))

        # If the remote URL is in CHECKING status and the response is successful, set it up
        if self.remote[base_url].status == CHECKING and 200 <= response.status_code < 400:
            self.remote.set_up(base_url)

        self.debug(
            f"◀◀ {response.status_code} {response.reason_phrase} "
            f"({_format_elapsed(response.elapsed)}{' cached' if is_response_from_cache else ''})",
            transaction=transaction,
        )

        # Filter out certain headers from the response. RFC 9110 §7.6.1 binds an intermediary in
        # both directions, so the upstream's connection-specific fields stop here just as the
        # client's do on the way out. `content-encoding` and the identifying `server`/`date` are
        # dropped for their own reasons, unrelated to the hop.
        dropped = hop_by_hop_names(response.headers) | {"server", "date", "content-encoding"}
        headers = {k: v for k, v in response.headers.multi_items() if k.lower() not in dropped}

        # Store the status class in the transaction extras for later use
        transaction.extras["status_class"] = f"{response.status_code // 100}xx"

        # Store cache status and age if response was cached
        if is_response_from_cache:
            transaction.extras["cached"] = True
            # Age is how long ago we stored it, measured by our own clock. The `Age` header cannot
            # stand in for that either: the origin sets it to describe its own cache, not ours.
            created_at = response.extensions.get("hishel_created_at")
            if created_at is not None:
                transaction.extras["cache_age"] = int(time() - created_at)

        return HttpResponse(response.content, status=response.status_code, headers=headers)

    async def _get_next_url_for(self, context) -> tuple[str, str]:
        base_url = self.remote.get_url()
        if _has_control_or_space(context.request.path):
            raise ProxyRoutingError(context.request.path)
        # Only the path component of the incoming request may influence the upstream URL: urlsplit
        # drops a leading scheme/host ("http://evil/", "//evil/"). The forwarded URL is the endpoint's
        # origin and base path followed by that raw path, byte for byte. It is never re-parsed as a
        # reference against the base (urljoin would read "/http://evil/" or "/user:42" as a scheme),
        # so the origin is fixed by construction.
        try:
            raw_path = urlsplit(context.request.path).path
        except ValueError as exc:  # "//[x/": an authority urlsplit cannot parse
            raise ProxyRoutingError(context.request.path) from exc
        # With no dot segment, nothing between here and the upstream (httpx, an upstream decoding once)
        # has anything left to resolve, so the path forwarded stays below the base path as sent.
        if _has_dot_segment(raw_path):
            raise ProxyRoutingError(context.request.path)
        base = urlsplit(base_url)
        forwarded_url = f"{base.scheme}://{base.netloc}{_base_path_of(base_url)}{raw_path.lstrip('/')}"
        full_url = forwarded_url + (f"?{urlencode(context.request.query)}" if context.request.query else "")
        if len(full_url) > MAX_FORWARDED_URL_LENGTH:
            raise RejectedRequest("Request path is too long.", status=414)
        return base_url, full_url

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
        transaction.elapsed = round(
            (datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 1000,
            2,
        )

        if isinstance(response, HttpError):
            transaction.extras["status_class"] = "ERR"
            self.warning(
                f"◀ {type(response).__name__} {response.message} ({transaction.elapsed}ms)",
                transaction=transaction,
            )
        elif isinstance(response, HttpResponse):
            reason = codes.get_reason_phrase(response.status)
            self.info(
                f"◀ {response.status} {reason} ({transaction.elapsed}ms)",
                transaction=transaction,
            )
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

    async def start_transaction(self, request: HttpRequest, *, tags=None) -> ProxyFilterEvent:
        """
        Create a new transaction from the incoming request, generating a new (random, but orderable according to the
        instant it happens) transaction ID.

        Once created, it runs the request filters, then dispatches the EVENT_TRANSACTION_STARTED event to allow storage
        applications (or anything else) to react to this creation, then it dispatches the EVENT_TRANSACTION_MESSAGE
        event to allow to react to the fact this transaction contained a request.

        :return: Transaction
        """
        # RFC 9110 §7.6.1: `Connection` applies to the message as received. Apply it now, before rules run, so a
        # header a rule injects later is not mistaken for one the client marked as hop-by-hop.
        for name in _connection_named_headers(request.headers):
            request.headers.popall(name, None)
        request.headers.popall("connection", None)

        # create the context, an event that will be passed through the transaction lifecycle.
        context = ProxyFilterEvent(
            self.name,
            request=request,
            transaction=Transaction(
                id=generate_transaction_id_ksuid(),
                type="http",
                started_at=datetime.now(UTC),
                endpoint=self.name,
                tags=tags,
            ),
        )

        request.extensions["transaction"] = context.transaction

        # If the request cache control asked for cache to be disabled, mark it in transaction.
        request_cache_control = request.headers.get("cache-control")
        if request_cache_control:
            request_cache_control = parse_cache_control(request_cache_control)
            if request_cache_control.no_cache:
                context.transaction.extras["no_cache"] = True

        # XXX for now, we use transaction "extras" to store searchable data for later
        context.transaction.extras["method"] = request.method

        self.info(f"▶ {request.method} {request.path}", transaction=context.transaction)

        # allow filtering the incoming messsage/transaction before the transaction is stored
        context.update(await self.filter_request(context))

        # dispatch transaction started event, after the filters so markers they set (skip-storage) are seen
        # we don't really want to await this, should run in background ? or use an async queue ?
        await self.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(context.transaction))

        # dispatch message event for request
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(context.transaction, request))

        return context


def _connection_named_headers(headers) -> set:
    """Header names the message's own `Connection` field marks as connection-specific."""
    return hop_by_hop_names(headers) - HOP_BY_HOP_HEADERS


@lru_cache
def _base_path_of(base_url: str) -> str:
    """The upstream subtree an endpoint exposes, as a path prefix ending in a slash.

    This is the part of the endpoint url that a relative reference resolves against, so a request with
    no dot segment always lands inside it. An endpoint url with no path of its own exposes the whole
    origin, which gives "/".
    """
    return urlsplit(base_url).path.rsplit("/", 1)[0] + "/"


def _has_control_or_space(raw_path: str) -> bool:
    """Whether a raw request path holds a byte no valid request target carries (<= 0x20 or 0x7f).

    URL parsers strip or drop such bytes (leading C0 and space, tabs and newlines anywhere), so a path
    holding one does not read the same before and after parsing. HTTP/1.1 refuses them, h2 lets them
    through in ":path".
    """
    return any(char <= " " or char == "\x7f" for char in raw_path)


_PATH_SEPARATOR = re.compile(r"[/\\]")
_DOT_SEGMENT = re.compile(r"\.{1,2}")
# Overlong UTF-8 forms of "." "/" and "\\" that lenient decoders accept (a strict one rejects them).
_OVERLONG_UTF8 = {
    b"\xc0\xae": b".",
    b"\xe0\x80\xae": b".",
    b"\xf0\x80\x80\xae": b".",
    b"\xc0\xaf": b"/",
    b"\xe0\x80\xaf": b"/",
    b"\xc1\x9c": b"\\",
    b"\xe0\x81\x9c": b"\\",
}
_MAX_DECODING_ROUNDS = 8


def _decoded_as_any_upstream_might(raw_path: str) -> str:
    """The path after every decoding a lenient upstream may apply: repeated percent-decoding, overlong
    UTF-8 and Unicode (NFKC) normalisation, until nothing changes."""
    data = raw_path.encode()
    for _ in range(_MAX_DECODING_ROUNDS):
        previous = data
        data = unquote_to_bytes(data)
        for overlong, char in _OVERLONG_UTF8.items():
            data = data.replace(overlong, char)
        data = unicodedata.normalize("NFKC", data.decode(errors="replace")).encode()
        if data == previous:
            break
    return data.decode()


def _has_dot_segment(raw_path: str) -> bool:
    """Whether a raw path holds a "." or ".." segment, as any normaliser on the way could read one.

    Separators are "/", "\\" and their encodings, dots may be literal or encoded, in any case and any
    mix. Beyond a plain decoding, a segment counts as a dot segment when an upstream may reduce it to
    one: ";" parameters are dropped ("..;"), a NUL truncates, and the path is decoded again, accepts
    overlong UTF-8 and applies Unicode normalisation (fullwidth dots). A dot inside a segment
    (".well-known", "v1.2", "a%2eb") is not a dot segment.
    """
    decoded = _decoded_as_any_upstream_might(raw_path)
    for segment in _PATH_SEPARATOR.split(decoded):
        segment = segment.split("\x00", 1)[0].split(";", 1)[0]
        if _DOT_SEGMENT.fullmatch(segment):
            return True
    return False


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
