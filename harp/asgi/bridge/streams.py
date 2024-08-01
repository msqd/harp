from typing import AsyncIterator, cast

from asgiref.typing import ASGIReceiveCallable
from httpx import AsyncByteStream


class AsyncStreamFromAsgiReceive(AsyncByteStream):
    def __init__(self, asgi_receive: ASGIReceiveCallable) -> None:
        self.asgi_receive = asgi_receive
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self._closed:
            raise RuntimeError("Whole stream has already been read.")
        while not self._closed:
            message = await self.asgi_receive()
            self._closed = not message.get("more_body", False)
            yield cast(bytes, message.get("body", b""))

    async def aclose(self) -> None:
        self._closed = True
