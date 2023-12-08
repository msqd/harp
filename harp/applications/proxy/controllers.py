from datetime import datetime
from urllib.parse import urljoin

import httpx
from httpx import codes

from harp import get_logger
from harp.core.asgi.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.core.asgi.events.message import MessageEvent
from harp.core.asgi.events.transaction import TransactionEvent
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.services.http import client
from harp.utils.guids import generate_transaction_id_ksuid

logger = get_logger(__name__)


class HttpProxyController:
    def __init__(self, target, *, dispatcher=None, name=None):
        self.target = target
        self.name = name
        self.dispatcher = dispatcher

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

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        # BEGIN TRANSACTION
        transaction = Transaction(
            id=generate_transaction_id_ksuid(), type=request.type, started_at=datetime.utcnow(), target=self.name
        )
        logger.debug(f"▶ {request.method} {request.path}", transaction_id=transaction.id)

        if self.dispatcher:
            # dispatch transaction started event
            # we don't really want to await this, should run in background ? or use an async queue ?
            await self.dispatcher.dispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction))

            # dispatch message event for request
            await self.dispatcher.dispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, request))

        # PROXY REQUEST
        request_headers = tuple(((k, v) for k, v in request.headers if k.lower() not in (b"host",)))
        request_content = await self._suboptimal_temporary_extract_request_content(request)

        url = urljoin(self.target, request.path) + (f"?{request.query_string}" if request.query_string else "")

        p_request: httpx.Request = client.build_request(
            request.method,
            url,
            headers=request_headers,
            content=request_content,
        )
        logger.debug(f"▶▶ {request.method} {url}", transaction_id=transaction.id)

        # PROXY RESPONSE
        p_response: httpx.Response = await client.send(p_request)
        logger.debug(
            f"◀◀ {p_response.status_code} {p_response.reason_phrase} ({p_response.elapsed.total_seconds()}s)",
            transaction_id=transaction.id,
        )

        response_headers = dict(
            (k, v)
            for k, v in p_response.headers.raw
            if k.lower() not in (b"server", b"date", b"content-encoding", b"content-length")
        )

        status = p_response.status_code
        await response.start(status=status, headers=response_headers)
        await response.body(p_response.content)

        # END TRANSACTION
        reason = codes.get_reason_phrase(status)
        spent = int((datetime.utcnow().timestamp() - transaction.started_at.timestamp()) * 100000) / 100
        logger.debug(f"◀ {status} {reason} ({spent}ms)", transaction_id=transaction.id)

        if self.dispatcher:
            # dispatch message event for response
            await self.dispatcher.dispatch(EVENT_TRANSACTION_MESSAGE, MessageEvent(transaction, response))

            # dispatch transaction ended event
            await self.dispatcher.dispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction))
