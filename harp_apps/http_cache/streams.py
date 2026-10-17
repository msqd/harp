"""Response bodies passed through the cache as they arrive, each closable whether read or not.

hishel wraps a body in plain iterators that close nothing, so a response the client stops reading would hold its
upstream connection until garbage collection. Each wrapper here passes ``aclose`` down to the upstream response.
"""

import typing as tp

import httpx


async def aclose_source(body) -> None:
    """Close a body if it can be closed: hishel's own bodies (a stored entry's) cannot, and need not."""
    aclose = getattr(body, "aclose", None)
    if aclose is not None:
        await aclose()


class UpstreamBody:
    """An upstream response's raw body, read as it arrives. Closing it releases the upstream connection."""

    def __init__(self, response: httpx.Response):
        self._response = response
        self._chunks: tp.Optional[tp.AsyncIterator[bytes]] = None

    def __aiter__(self) -> "UpstreamBody":
        return self

    async def __anext__(self) -> bytes:
        if self._chunks is None:
            self._chunks = self._response.aiter_raw()
        return await anext(self._chunks)

    async def aclose(self) -> None:
        await self._response.aclose()


def body_decoder(content_encoding: tp.Optional[str]):
    """The decoder httpx applies to a body sent with this ``Content-Encoding``, the one the proxy reads it through.

    Built by httpx itself, so the cache measures a body exactly as the proxy does."""
    headers = [("content-encoding", content_encoding)] if content_encoding else []
    return httpx.Response(200, headers=headers)._get_content_decoder()


class StoredOnceRead:
    """Passes a body through and awaits ``on_end`` with it once read to its end, unless it is over ``limit`` bytes.

    The body is measured decoded, as the client receives it, whatever its size on the wire. At most ``limit`` bytes are
    held. A body left unread, undecodable or longer than the limit never reaches ``on_end``.
    """

    def __init__(
        self,
        source,
        *,
        limit: int,
        on_end: tp.Callable[[bytes], tp.Awaitable[None]],
        content_encoding: tp.Optional[str] = None,
    ):
        self._source = source
        self._chunks = aiter(source)
        self._limit = limit
        self._on_end = on_end
        self._decoder = body_decoder(content_encoding)
        self._body = bytearray()
        self._decoded_size = 0
        self._over = False
        self._ended = False

    def __aiter__(self) -> "StoredOnceRead":
        return self

    async def __anext__(self) -> bytes:
        try:
            chunk = await anext(self._chunks)
        except StopAsyncIteration:
            self._measure(self._decoder.flush)
            if not self._ended and not self._over:
                self._ended = True
                await self._on_end(bytes(self._body))
            raise
        if not self._over:
            self._body += chunk
            self._measure(lambda: self._decoder.decode(chunk))
        return chunk

    def _measure(self, decode: tp.Callable[[], bytes]) -> None:
        if self._over:
            return
        try:
            self._decoded_size += len(decode())
        except httpx.DecodingError:
            self._decoded_size = self._limit + 1
        if self._decoded_size > self._limit or len(self._body) > self._limit:
            self._over = True
            self._body.clear()

    async def aclose(self) -> None:
        await aclose_source(self._source)


class ClosableByteStream(httpx.AsyncByteStream):
    """The httpx side of a cached or forwarded body: closing the response closes the body."""

    def __init__(self, body):
        self._body = body

    async def __aiter__(self) -> tp.AsyncIterator[bytes]:
        async for chunk in self._body:
            yield chunk

    async def aclose(self) -> None:
        await aclose_source(self._body)
