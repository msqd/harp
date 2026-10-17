import asyncio
from typing import AsyncIterator, Optional

import aiohttp
import httpx
from aiohttp import hdrs

from harp.utils.bytes import HEADER_ENCODING

# What httpx's default transport allows (httpx.Limits and its keepalive_expiry).
MAX_CONNECTIONS = 100
KEEPALIVE_EXPIRY = 5.0


def _translate(exc: BaseException, request: httpx.Request) -> httpx.TransportError:
    """The httpx exception the proxy knows how to answer for, for what aiohttp raised."""
    if isinstance(exc, aiohttp.ConnectionTimeoutError):
        return httpx.ConnectTimeout(str(exc), request=request)
    if isinstance(exc, (asyncio.TimeoutError, aiohttp.ServerTimeoutError)):
        return httpx.ReadTimeout(str(exc), request=request)
    if isinstance(exc, aiohttp.ClientConnectorError):
        return httpx.ConnectError(str(exc), request=request)
    if isinstance(exc, (aiohttp.ServerDisconnectedError, aiohttp.ClientPayloadError, aiohttp.ClientResponseError)):
        return httpx.RemoteProtocolError(str(exc) or type(exc).__name__, request=request)
    if isinstance(exc, aiohttp.ClientOSError):
        return httpx.ReadError(str(exc), request=request)
    return httpx.TransportError(str(exc) or type(exc).__name__, request=request)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: aiohttp.ClientResponse, request: httpx.Request):
        self._response = response
        self._request = request

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self._response.content.iter_any():
                yield chunk
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise _translate(exc, self._request) from exc

    async def aclose(self) -> None:
        self._response.release()


class AiohttpTransport(httpx.AsyncBaseTransport):
    """
    An httpx transport sending requests with aiohttp instead of httpcore: the httpx Request/Response contract stays,
    so hishel and the filters keep working on top.

    Bodies reach the wire and come back untouched: no header added, no redirect followed, no content decoding (httpx
    decodes when the content is read, as with its own transport).
    """

    def __init__(self, *, verify: bool = True, retries: int = 0):
        if retries:
            raise ValueError("The aiohttp transport does not support `retries`.")
        self._verify = verify
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        # Created on first use: it must belong to the running loop, which the service container does not know.
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=MAX_CONNECTIONS,
                    keepalive_timeout=KEEPALIVE_EXPIRY,
                    ssl=None if self._verify else False,
                ),
                cookie_jar=aiohttp.DummyCookieJar(),
                auto_decompress=False,
                skip_auto_headers=(hdrs.ACCEPT, hdrs.ACCEPT_ENCODING, hdrs.USER_AGENT, hdrs.CONTENT_TYPE),
            )
        return self._session

    @staticmethod
    def _timeout(request: httpx.Request) -> aiohttp.ClientTimeout:
        timeout = request.extensions.get("timeout", {})
        return aiohttp.ClientTimeout(
            total=None,
            connect=timeout.get("pool"),
            sock_connect=timeout.get("connect"),
            sock_read=timeout.get("read"),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        headers = [(name.decode(HEADER_ENCODING), value.decode(HEADER_ENCODING)) for name, value in request.headers.raw]
        try:
            response = await self._get_session().request(
                request.method,
                str(request.url),
                data=body or None,
                headers=headers,
                allow_redirects=False,
                timeout=self._timeout(request),
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise _translate(exc, request) from exc

        return httpx.Response(
            response.status,
            headers=list(response.raw_headers),
            stream=_ResponseStream(response, request),
            extensions={"reason_phrase": (response.reason or "").encode(), "http_version": b"HTTP/1.1"},
        )

    async def aclose(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
