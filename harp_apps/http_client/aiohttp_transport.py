import asyncio
import ssl
from typing import AsyncIterator, Optional, Union

import aiohttp
import httpx
from aiohttp import hdrs

from harp.utils.bytes import HEADER_ENCODING

# What httpx's default transport allows.
DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=None, keepalive_expiry=5.0)


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


_WAY_OUT = " Set `http_client.transport.type: httpx.AsyncHTTPTransport` to keep httpx's transport."


class AiohttpTransport(httpx.AsyncBaseTransport):
    """
    An httpx transport sending requests with aiohttp instead of httpcore: the httpx Request/Response contract stays,
    so hishel and the filters keep working on top.

    Bodies reach the wire and come back untouched: no header added, no redirect followed, no content decoding (httpx
    decodes when the content is read, as with its own transport).
    """

    def __init__(
        self,
        *,
        verify: Union[bool, ssl.SSLContext] = True,
        retries: int = 0,
        limits: httpx.Limits = DEFAULT_LIMITS,
        http2: bool = False,
    ):
        # What aiohttp cannot honour is refused here, never ignored.
        if retries:
            raise ValueError("The aiohttp transport cannot honour `retries`: aiohttp does not retry." + _WAY_OUT)
        if not isinstance(verify, (bool, ssl.SSLContext)):
            raise ValueError(
                "The aiohttp transport cannot honour this `verify`: give a boolean or an SSLContext." + _WAY_OUT
            )
        if limits.max_keepalive_connections is not None:
            raise ValueError(
                "The aiohttp transport cannot honour `max_keepalive_connections`: aiohttp has no such limit." + _WAY_OUT
            )
        if http2:
            raise ValueError("The aiohttp transport cannot honour `http2`: aiohttp speaks HTTP/1.1 only." + _WAY_OUT)
        self._verify = verify
        self._limits = limits
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        # Created on first use: it must belong to the running loop, which the service container does not know.
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=self._limits.max_connections or 0,
                    keepalive_timeout=self._limits.keepalive_expiry or 0,
                    ssl=self._verify if isinstance(self._verify, ssl.SSLContext) else (None if self._verify else False),
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
        chunked = "transfer-encoding" in request.headers
        body = request.stream if chunked else await request.aread()
        headers = [
            (name.decode(HEADER_ENCODING), value.decode(HEADER_ENCODING))
            for name, value in request.headers.raw
            if not (chunked and name.lower() == b"transfer-encoding")  # aiohttp sets it when asked to chunk
        ]
        try:
            response = await self._get_session().request(
                request.method,
                str(request.url),
                data=body or None,
                headers=headers,
                chunked=chunked or None,
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
