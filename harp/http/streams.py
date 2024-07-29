from typing import AsyncIterator, Iterator

from .typing import HttpRequestBridge


class AsyncByteStream:
    async def __aiter__(self) -> AsyncIterator[bytes]:
        raise NotImplementedError("The '__aiter__' method must be implemented.")  # pragma: no cover
        yield b""  # pragma: no cover

    async def aclose(self) -> None:
        pass


class SyncByteStream:
    def __iter__(self) -> Iterator[bytes]:
        raise NotImplementedError("The '__iter__' method must be implemented.")  # pragma: no cover
        yield b""  # pragma: no cover

    def close(self) -> None:
        """
        Subclasses can override this method to release any network resources
        after a request/response cycle is complete.
        """


class ByteStream(AsyncByteStream):
    def __init__(self, stream: bytes) -> None:
        self._stream = stream

    def __iter__(self) -> Iterator[bytes]:
        yield self._stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self._stream


class AsyncStreamFromAsgiBridge(AsyncByteStream):
    def __init__(self, request_bridge: HttpRequestBridge) -> None:
        self._bridge = request_bridge

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._bridge.stream():
            yield chunk
