from datetime import UTC, datetime
from functools import cached_property
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import httpcore
import httpx
from httpx import AsyncClient, codes
from whistle import IAsyncEventDispatcher

from harp import __parsed_version__, get_logger
from harp.asgi.events import HttpMessageEvent, TransactionEvent
from harp.http import BaseHttpMessage, HttpError, HttpRequest, HttpResponse
from harp.http.utils import parse_cache_control
from harp.models import Transaction
from harp.settings import USE_PROMETHEUS
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.performances import performances_observer
from harp.utils.tpdex import tpdex

from .events import (
    EVENT_FILTER_PROXY_REQUEST,
    EVENT_FILTER_PROXY_RESPONSE,
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    ProxyFilterEvent,
)

logger = get_logger(__name__)

_prometheus = None
if USE_PROMETHEUS:
    from prometheus_client import Counter, Histogram

    _prometheus = {
        "call": Counter("proxy_calls", "Requests to the proxy.", ["name", "method"]),
        "time.full": Histogram("proxy_time_full", "Requests to the proxy including overhead.", ["name", "method"]),
        "time.forward": Histogram("proxy_time_forward", "Forward time.", ["name", "method"]),
    }


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

    def __init__(
        self,
        url,
        *,
        http_client: AsyncClient,
        dispatcher: Optional[IAsyncEventDispatcher] = None,
        name=None,
        logging=True,
    ):
        self.http_client = http_client
        self.url = url or self.url
        self.name = name or self.name
        self._logging = logging
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

    async def __call__(self, request: HttpRequest):
        """Handle an incoming request and proxy it to the configured URL.

        :param request: ASGI request
        :param response: ASGI response
        :return:

        """

        labels = {"name": self.name or "-", "method": request.method}

        with performances_observer("proxy", labels=labels):
            # create an envelope to override things, without touching the original request
            context = ProxyFilterEvent(self.name, request=request)
            await self.adispatch(EVENT_FILTER_PROXY_REQUEST, context)

            # override a few required headers. That may be done in the httpx request instead of here.
            # And that would remove the need for WrappedHttpRequest? Maybe not because of our custom filters.
            context.request.headers["host"] = self.parsed_url.netloc
            if self.user_agent:
                context.request.headers["user-agent"] = self.user_agent

            # create transaction (shouldn't that be before the filter operation ? it's debatable.)
            transaction = await self._create_transaction_from_request(
                context.request, tags=self._extract_tags_from_request(context.request)
            )
            await context.request.aread()
            url = urljoin(self.url, context.request.path) + (
                f"?{urlencode(context.request.query)}" if context.request.query else ""
            )

            if not context.response:
                with performances_observer("http", labels=labels):
                    # PROXY REQUEST
                    remote_request: httpx.Request = self.http_client.build_request(
                        context.request.method,
                        url,
                        headers=list(context.request.headers.items()),
                        content=context.request.body,
                        extensions={"harp": {"endpoint": self.name}},
                    )
                    self.debug(
                        f"▶▶ {context.request.method} {url}",
                        transaction=transaction,
                        extensions=remote_request.extensions,
                    )

                    # PROXY RESPONSE
                    try:
                        remote_response: httpx.Response = await self.http_client.send(remote_request)
                    except (httpcore.NetworkError, httpx.NetworkError) as exc:
                        transaction.extras["status_class"] = "ERR"
                        await self.end_transaction(transaction, HttpError("Unavailable", exception=exc))
                        # todo add web debug information if we are not on a production env
                        return HttpResponse(
                            "Service Unavailable (remote server unavailable)", status=503, content_type="text/plain"
                        )
                    except (httpcore.TimeoutException, httpx.TimeoutException) as exc:
                        transaction.extras["status_class"] = "ERR"
                        await self.end_transaction(transaction, HttpError("Timeout", exception=exc))
                        # todo add web debug information if we are not on a production env
                        return HttpResponse(
                            "Gateway Timeout (remote server timeout)", status=504, content_type="text/plain"
                        )
                    except (httpcore.RemoteProtocolError, httpx.RemoteProtocolError):
                        transaction.extras["status_class"] = "ERR"
                        await self.end_transaction(transaction, HttpError("Remote server disconnected"))
                        return HttpResponse(
                            "Bad Gateway (remote server disconnected)", status=502, content_type="text/plain"
                        )
                    await remote_response.aread()
                    await remote_response.aclose()

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

            await self.end_transaction(transaction, context.response)

            return context.response

    async def end_transaction(self, transaction, response: BaseHttpMessage):
        spent = int((datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 100000) / 100
        transaction.finished_at = datetime.now(UTC)
        transaction.elapsed = spent

        if isinstance(response, HttpError):
            self.warning(f"◀ {type(response).__name__} {response.message} ({spent}ms)", transaction=transaction)
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

        self.info(f"▶ {request.method} {request.path}", transaction=transaction)

        # dispatch transaction started event
        # we don't really want to await this, should run in background ? or use an async queue ?
        await self.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction))

        # dispatch message event for request
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, request))

        return transaction

    def _extract_tags_from_request(self, request: HttpRequest):
        """
        Convert special request headers (x-harp-*) into tags (key-value pairs) that we'll attach to the
        transaction. Headers are "consumed", meaning they are removed from the request headers.
        """

        tags = {}
        headers_to_remove = []

        for header in request.headers:
            lower_header = header.lower()
            if lower_header.startswith("x-harp-"):
                tags[lower_header[7:]] = request.headers[header]
                headers_to_remove.append(header)

        for header in headers_to_remove:
            request.headers.pop(header)

        return tags

    def __repr__(self):
        return f"{type(self).__name__}({self.url!r}, name={self.name!r})"
