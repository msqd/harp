from urllib.parse import urljoin

import httpx

from harp import get_logger
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.services.http import client

logger = get_logger(__name__)


class HttpProxyController:
    def __init__(self, target, *, name=None):
        self.target = target
        self.name = name

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
        request_headers = tuple(((k, v) for k, v in request.headers if k.lower() not in (b"host",)))
        request_content = await self._suboptimal_temporary_extract_request_content(request)
        logger_kwargs = dict(transaction_id=getattr(request, "transaction_id", None))

        url = urljoin(self.target, request.path) + (f"?{request.query_string}" if request.query_string else "")

        p_request: httpx.Request = client.build_request(
            request.method,
            url,
            headers=request_headers,
            content=request_content,
        )
        logger.info(f"▶▶ {request.method} {url}", **logger_kwargs)
        p_response: httpx.Response = await client.send(p_request)
        logger.info(
            f"◀◀ {p_response.status_code} {p_response.reason_phrase} ({p_response.elapsed.total_seconds()}s)",
            **logger_kwargs,
        )

        response_headers = dict(
            (k, v)
            for k, v in p_response.headers.raw
            if k.lower() not in (b"server", b"date", b"content-encoding", b"content-length")
        )

        await response.start(status=p_response.status_code, headers=response_headers)
        await response.body(p_response.content)
