from datetime import timedelta
from typing import AsyncIterator, Optional

import httpx
from pyreqwest import exceptions
from pyreqwest.client import Client, ClientBuilder

from harp.utils.bytes import HEADER_ENCODING

# What httpx's default transport allows.
DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0)

_ERRORS = (
    (exceptions.ConnectTimeoutError, httpx.ConnectTimeout),
    (exceptions.PoolTimeoutError, httpx.PoolTimeout),
    (exceptions.WriteTimeoutError, httpx.WriteTimeout),
    (exceptions.RequestTimeoutError, httpx.ReadTimeout),
    (exceptions.ReadTimeoutError, httpx.ReadTimeout),
    (exceptions.ConnectError, httpx.ConnectError),
    (exceptions.WriteError, httpx.WriteError),
    (exceptions.ReadError, httpx.ReadError),
    (exceptions.NetworkError, httpx.NetworkError),
)


def _translate(exc: BaseException, request: httpx.Request) -> httpx.TransportError:
    """The httpx exception the proxy knows how to answer for, for what pyreqwest raised."""
    if "connection closed before message completed" in str(exc):
        # reqwest reports a peer that hangs up without answering as a connect error.
        return httpx.RemoteProtocolError(str(exc), request=request)
    for source, target in _ERRORS:
        if isinstance(exc, source):
            return target(str(exc), request=request)
    return httpx.RemoteProtocolError(str(exc) or type(exc).__name__, request=request)


def _seconds(value: Optional[float]) -> Optional[timedelta]:
    return None if value is None else timedelta(seconds=value)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, context, response, request: httpx.Request):
        self._context = context
        self._response = response
        self._request = request

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            while (chunk := await self._response.body_reader.read_chunk()) is not None:
                yield bytes(chunk)
        except exceptions.PyreqwestError as exc:
            raise _translate(exc, self._request) from exc

    async def aclose(self) -> None:
        await self._context.__aexit__(None, None, None)


class PyreqwestTransport(httpx.AsyncBaseTransport):
    """
    An httpx transport sending requests with pyreqwest (reqwest, in Rust) instead of httpcore.

    NON-CONFORMING, for benchmarking only, never a candidate to ship: hyper's header map loses the order of headers
    across names, the interleaving of duplicates and their casing, and reqwest adds ``Accept`` and ``User-Agent``
    when absent. The conformance suite lists these as strict expected failures. It exists to measure what a native
    client could give at best.
    """

    def __init__(self, *, verify: bool = True, retries: int = 0, limits: httpx.Limits = DEFAULT_LIMITS):
        # What pyreqwest cannot honour is refused here, never ignored.
        if retries:
            raise ValueError("The pyreqwest transport cannot honour `retries`: reqwest does not retry.")
        if not isinstance(verify, bool):
            raise ValueError("The pyreqwest transport cannot honour this `verify`: give a boolean.")
        self._verify = verify
        self._limits = limits
        # reqwest takes its timeouts when the client is built, httpx gives them with each request.
        self._clients: dict[tuple, Client] = {}

    def _client_for(self, request: httpx.Request) -> Client:
        timeout = request.extensions.get("timeout", {})
        key = tuple(timeout.get(name) for name in ("connect", "read", "pool"))
        if key not in self._clients:
            connect, read, pool = map(_seconds, key)
            builder = (
                ClientBuilder()
                .http1_only()
                .user_agent("")
                .follow_redirects(False)
                .gzip(False)
                .brotli(False)
                .deflate(False)
                .zstd(False)
                .danger_accept_invalid_certs(not self._verify)
            )
            if self._limits.max_connections is not None:
                builder = builder.max_connections(self._limits.max_connections)
            if self._limits.max_keepalive_connections is not None:
                builder = builder.pool_max_idle_per_host(self._limits.max_keepalive_connections)
            if self._limits.keepalive_expiry is not None:
                builder = builder.pool_idle_timeout(_seconds(self._limits.keepalive_expiry))
            if connect:
                builder = builder.connect_timeout(connect)
            if read:
                builder = builder.read_timeout(read)
            if pool:
                builder = builder.pool_timeout(pool)
            self._clients[key] = builder.build()
        return self._clients[key]

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        builder = self._client_for(request).request(request.method, str(request.url))
        builder = builder.headers(
            [(name.decode(HEADER_ENCODING), value.decode(HEADER_ENCODING)) for name, value in request.headers.raw]
        )
        if "transfer-encoding" in request.headers:
            builder = builder.body_stream(request.stream)
        elif body := await request.aread():
            builder = builder.body_bytes(body)
        context = builder.build_streamed()
        try:
            response = await context.__aenter__()
        except exceptions.PyreqwestError as exc:
            raise _translate(exc, request) from exc

        return httpx.Response(
            response.status,
            headers=[
                (name.encode(HEADER_ENCODING), value.encode(HEADER_ENCODING))
                for name, value in response.headers.items()
            ],
            stream=_ResponseStream(context, response, request),
            extensions={"http_version": b"HTTP/1.1"},
        )

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
