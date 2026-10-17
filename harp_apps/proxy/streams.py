from typing import AsyncIterator, Awaitable, Callable, Optional

from httpx import AsyncByteStream, Response


class UpstreamResponseStream(AsyncByteStream):
    """The body of an upstream response, decoded, read as it arrives. Closing it releases the upstream connection."""

    def __init__(self, response: Response):
        self._response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._response.aiter_bytes():
            yield chunk

    async def aclose(self) -> None:
        await self._response.aclose()


class RecordingStream(AsyncByteStream):
    """Passes a body through as it arrives and keeps at most its first ``limit`` bytes.

    ``on_end`` is awaited once, when the body is over: with ``None`` once it was read to the end or abandoned (see
    :attr:`abandoned`), with the exception that interrupted it otherwise. The memory held is the recorded prefix, never
    the whole body.
    """

    def __init__(
        self,
        stream: AsyncByteStream,
        *,
        limit: int,
        on_end: Callable[["RecordingStream", Optional[Exception]], Awaitable[None]],
    ):
        self._stream = stream
        self._limit = limit
        self._on_end = on_end
        self._recorded = bytearray()
        self._size = 0
        self._exhausted = False
        self._ended = False

    @property
    def recorded(self) -> bytes:
        """The first ``limit`` bytes of the body read so far."""
        return bytes(self._recorded)

    @property
    def abandoned(self) -> bool:
        """Whether whoever read the body stopped before its end: the client went away."""
        return not self._exhausted

    @property
    def truncated(self) -> bool:
        """Whether more of the body was read than was recorded."""
        return self._size > self._limit

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self._stream:
                self._record(chunk)
                yield chunk
            self._exhausted = True
        except Exception as exc:
            await self._end(exc)
            raise
        finally:
            await self._end(None)

    async def aclose(self) -> None:
        try:
            await self._stream.aclose()
        finally:
            await self._end(None)

    def _record(self, chunk: bytes) -> None:
        self._size += len(chunk)
        room = self._limit - len(self._recorded)
        if room > 0:
            self._recorded += chunk[:room]

    async def _end(self, error: Optional[Exception]) -> None:
        if self._ended:
            return
        self._ended = True
        await self._on_end(self, error)
