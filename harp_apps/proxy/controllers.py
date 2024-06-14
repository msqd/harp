from datetime import UTC, datetime
from functools import cached_property
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from hishel._headers import parse_cache_control
from httpx import AsyncClient, codes
from whistle import IAsyncEventDispatcher

from harp import __parsed_version__, get_logger
from harp.asgi.events import MessageEvent, TransactionEvent
from harp.http import BaseHttpMessage, HttpError, HttpRequest, HttpResponse
from harp.http.requests import WrappedHttpRequest
from harp.models import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.tpdex import tpdex

from .events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED

logger = get_logger(__name__)


class HttpProxyController:
    name: str = None
    """Controller name, also refered as endpoint name (for example in
    :class:`Transaction <harp.models.Transaction>`)."""

    user_agent: str = None
    """User agent to use when proxying requests (will default to harp/<version>)."""

    _dispatcher: Optional[IAsyncEventDispatcher] = None
    """Event dispatcher for this controller."""

    url: str
    """Base URL to proxy requests to."""

    @cached_property
    def dispatcher(self):
        """Read-only reference to the event dispatcher."""
        return self._dispatcher

    def __init__(self, url, *, http_client: AsyncClient, dispatcher=None, name=None):
        self.http_client = http_client
        self.url = url or self.url
        self.name = name or self.name
        self._dispatcher = dispatcher or self._dispatcher

        self.parsed_url = urlparse(self.url)

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

    async def __call__(self, request: HttpRequest):
        """Handle an incoming request and proxy it to the configured URL.

        :param request: ASGI request
        :param response: ASGI response
        :return:

        """

        # create an envelope to override things, without touching the original request
        request = WrappedHttpRequest(request)
        request.headers["host"] = self.parsed_url.netloc

        # BEGIN TRANSACTION AND PREPARE DATA FOR PROXY REQUEST
        tags = {}

        for header in request.headers:
            header = header.lower()
            if header.startswith("x-harp-"):
                tags[header[7:]] = request.headers.pop(header)

        # override user agent (later, may be customizable behavior)
        if self.user_agent:
            request.headers["user-agent"] = self.user_agent

        transaction = await self._create_transaction_from_request(request, tags=tags)
        await request.join()
        url = urljoin(self.url, request.path) + (f"?{urlencode(request.query)}" if request.query else "")

        # PROXY REQUEST
        p_request: httpx.Request = self.http_client.build_request(
            request.method, url, headers=list(request.headers.items()), content=request.body
        )
        logger.debug(f"▶▶ {request.method} {url}", transaction_id=transaction.id)

        # PROXY RESPONSE
        try:
            p_response: httpx.Response = await self.http_client.send(p_request)
        except httpx.ConnectError as exc:
            transaction.extras["status_class"] = "ERR"
            await self.end_transaction(transaction, HttpError("Unavailable", exception=exc))
            # todo add web debug information if we are not on a production env
            return HttpResponse(
                "Service Unavailable (remote server unavailable)", status=503, content_type="text/plain"
            )
        except httpx.TimeoutException as exc:
            transaction.extras["status_class"] = "ERR"
            await self.end_transaction(transaction, HttpError("Timeout", exception=exc))
            # todo add web debug information if we are not on a production env
            return HttpResponse("Gateway Timeout (remote server timeout)", status=504, content_type="text/plain")

        logger.debug(
            f"◀◀ {p_response.status_code} {p_response.reason_phrase} ({p_response.elapsed.total_seconds()}s)",
            transaction_id=transaction.id,
        )

        response_status = p_response.status_code
        response_headers = {
            k: v
            for k, v in p_response.headers.multi_items()
            if k.lower() not in ("server", "date", "content-encoding", "content-length")
        }
        # XXX for now, we use transaction "extras" to store searchable data for later
        transaction.extras["status_class"] = f"{response_status // 100}xx"

        if p_response.extensions.get("from_cache"):
            transaction.extras["cached"] = p_response.extensions.get("cache_metadata", {}).get("cache_key", True)

        response = HttpResponse(p_response.content, status=response_status, headers=response_headers)

        await self.end_transaction(transaction, response)

        return response

    async def end_transaction(self, transaction, response: BaseHttpMessage):
        spent = int((datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 100000) / 100
        transaction.finished_at = datetime.now(UTC)
        transaction.elapsed = spent

        if isinstance(response, HttpError):
            logger.error(f"◀ {type(response).__name__} {response.message} ({spent}ms)", transaction_id=transaction.id)
        elif isinstance(response, HttpResponse):
            reason = codes.get_reason_phrase(response.status)
            logger.debug(f"◀ {response.status} {reason} ({spent}ms)", transaction_id=transaction.id)
        else:
            raise ValueError(f"Invalid final message type: {type(response)}")

        if transaction.extras.get("status_class") == "ERR":
            transaction.tpdex = 0
        else:
            transaction.tpdex = tpdex(transaction.elapsed)

        # dispatch message event for response
        # TODO delay after response is sent ?
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, response))
        # dispatch transaction ended event
        # TODO delay after response is sent ?
        await self.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction))

    async def _create_transaction_from_request(self, request: HttpRequest, *, tags=None):
        transaction = Transaction(
            id=generate_transaction_id_ksuid(),
            type="http",
            started_at=datetime.now(UTC),
            endpoint=self.name,
            tags=tags,
        )

        request_cache_control = request.headers.get("cache-control")
        if request_cache_control:
            request_cache_control = parse_cache_control([request_cache_control])
            if request_cache_control.no_cache:
                transaction.extras["no_cache"] = True

        # XXX for now, we use transaction "extras" to store searchable data for later
        transaction.extras["method"] = request.method

        logger.debug(f"▶ {request.method} {request.path}", transaction_id=transaction.id)

        # dispatch transaction started event
        # we don't really want to await this, should run in background ? or use an async queue ?
        await self.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction))

        # dispatch message event for request
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, request))

        return transaction

    def __repr__(self):
        return f"{type(self).__name__}({self.url!r}, name={self.name!r})"
