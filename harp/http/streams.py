from typing import AsyncIterator, Iterator

from httpx import AsyncByteStream

from .typing import HttpRequestBridge


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
