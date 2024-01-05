from datetime import UTC, datetime
from functools import cached_property
from typing import Optional
from urllib.parse import urljoin

import httpx
from httpx import codes
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.core.asgi.events import MessageEvent, TransactionEvent
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.services.http import client
from harp.utils.guids import generate_transaction_id_ksuid

logger = get_logger(__name__)


class HttpProxyController:
    name: str = None
    """Controller name, also refered as endpoint name (for example in
    :class:`Transaction <harp.core.models.transactions.Transaction>`)."""

    _dispatcher: Optional[IAsyncEventDispatcher] = None
    """Event dispatcher for this controller."""

    url: str
    """Base URL to proxy requests to."""

    @cached_property
    def dispatcher(self):
        """Read-only reference to the event dispatcher."""
        return self._dispatcher

    def __init__(self, url, *, dispatcher=None, name=None):
        self.url = url or self.url
        self.name = name or self.name
        self._dispatcher = dispatcher or self._dispatcher

    async def adispatch(self, event_id, event=None):
        """
        Shortcut method to dispatch an event using the controller's dispatcher, if there is one.

        :return: :class:`IEvent <whistle.IEvent>` or None
        """
        if self._dispatcher:
            return await self._dispatcher.adispatch(event_id, event)

    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        """Handle an incoming request and proxy it to the configured URL.

        :param request: ASGI request
        :param response: ASGI response
        :return:

        """
        # BEGIN TRANSACTION
        transaction = Transaction(
            id=generate_transaction_id_ksuid(),
            type=request.type,
            started_at=datetime.now(UTC),
            endpoint=self.name,
        )
        logger.debug(f"▶ {request.method} {request.path}", transaction_id=transaction.id)

        # XXX for now, we use transaction "extras" to store searchable data for later
        transaction.extras["method"] = request.method

        # dispatch transaction started event
        # we don't really want to await this, should run in background ? or use an async queue ?
        await self.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction))

        # dispatch message event for request
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, request))

        # PROXY REQUEST
        request_headers = tuple(((k, v) for k, v in request.headers.items() if k.lower() not in ("host",)))
        request_content = await self._suboptimal_temporary_extract_request_content(request)

        url = urljoin(self.url, request.path) + (f"?{request.query_string}" if request.query_string else "")

        p_request: httpx.Request = client.build_request(
            request.method,
            url,
            headers=request_headers,
            content=request_content,
        )
        logger.debug(f"▶▶ {request.method} {url}", transaction_id=transaction.id)

        # PROXY RESPONSE
        try:
            p_response: httpx.Response = await client.send(p_request)
        except httpx.TimeoutException:
            logger.error(f"▶▶ {request.method} {url} (timeout)", transaction_id=transaction.id)
            await response.start(status=504)
            return

        logger.debug(
            f"◀◀ {p_response.status_code} {p_response.reason_phrase} ({p_response.elapsed.total_seconds()}s)",
            transaction_id=transaction.id,
        )

        status = p_response.status_code

        # XXX for now, we use transaction "extras" to store searchable data for later
        transaction.extras["status_class"] = f"{status // 100}xx"

        response.headers.update(
            (k, v)
            for k, v in p_response.headers.multi_items()
            if k.lower() not in ("server", "date", "content-encoding", "content-length")
        )
        await response.start(status=status)
        await response.body(p_response.content)

        # END TRANSACTION
        reason = codes.get_reason_phrase(status)
        spent = int((datetime.now(UTC).timestamp() - transaction.started_at.timestamp()) * 100000) / 100
        logger.debug(f"◀ {status} {reason} ({spent}ms)", transaction_id=transaction.id)

        # dispatch message event for response
        await self.adispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, response))

        transaction.finished_at = datetime.now(UTC)
        transaction.elapsed = spent

        # dispatch transaction ended event
        await self.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction))

    async def _suboptimal_temporary_extract_request_content(self, request: ASGIRequest):
        """
        todo we should not remove the buffering ability, httpx allows us to stream the request body but for that we need
        some kind of stream processor that yields and store the chunks.

        :param ctx:
        :return:
        """
        messages = []
        more_body = True
        while more_body:
            message = await request.receive()
            more_body = message.get("more_body", False)
            part = message.get("body", b"")
            messages.append(part)
            request._body += part
        return b"".join(messages) if len(messages) else None

    def __repr__(self):
        return f"{type(self).__name__}({self.url!r}, name={self.name!r})"
