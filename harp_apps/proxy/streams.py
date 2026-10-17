import asyncio
from time import monotonic
from typing import AsyncIterator, Awaitable, Callable, Optional

from httpx import AsyncByteStream, Response

from harp.http import RejectedRequest

REQUEST_TIMEOUT_STATUS_CODE = 408


class RequestBodyTooSlow(RejectedRequest):
    """Raised while reading a request body that arrives slower than the minimum rate."""

    def __init__(self):
        super().__init__("Request body too slow", status=REQUEST_TIMEOUT_STATUS_CODE)


class MinRateStream(AsyncByteStream):
    """Passes a request body through, and gives up on a client sending it too slowly.

    Once ``grace_period`` seconds have elapsed, the body must have reached an average of ``min_rate`` bytes per second,
    otherwise :class:`RequestBodyTooSlow` is raised, without waiting for the next chunk. A ``min_rate`` of zero
    disables the check.
    """

    def __init__(self, stream: AsyncByteStream, *, min_rate: float, grace_period: float):
        self._stream = stream
        self._min_rate = min_rate
        self._grace_period = grace_period

    def _deadline(self, start: float, received: int) -> float:
        """Moment at which, should nothing more arrive, the average rate falls below the minimum."""
        return start + max(self._grace_period, received / self._min_rate)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if not self._min_rate:
            async for chunk in self._stream:
                yield chunk
            return

        start, received = monotonic(), 0
        chunks = aiter(self._stream)
        while True:
            try:
                chunk = await asyncio.wait_for(anext(chunks), max(self._deadline(start, received) - monotonic(), 0))
            except StopAsyncIteration:
                return
            except TimeoutError:
                raise RequestBodyTooSlow() from None
            received += len(chunk)
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


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
