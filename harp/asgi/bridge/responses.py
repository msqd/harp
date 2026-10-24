import asyncio
from contextlib import aclosing, suppress
from typing import TYPE_CHECKING, Optional

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable
from multidict import CIMultiDictProxy

from harp.utils.bytes import ensure_bytes, header_bytes

if TYPE_CHECKING:
    from harp.http import HttpResponse


_END = object()


class _ClientGone(Exception):
    """The client disconnected before the end of the response body."""


class HttpResponseAsgiBridge:  # todo protocol HttpResponseBridge
    """Implements the ability of sending our HttpResponse object over the asgi protocol.

    A body held in memory goes out in one message. A streamed body goes out chunk by chunk, each chunk sent before the
    next one is read, and its stream is closed once sent or once the client is gone.

    Given ``receive``, the bridge listens for the client's ``http.disconnect`` while it streams: the server may keep
    accepting what is sent to a client that is gone, so without it the whole body would still be read."""

    def __init__(self, response: "HttpResponse", send: ASGISendCallable, receive: Optional[ASGIReceiveCallable] = None):
        self.response = response
        self.asgi_send = send
        self.asgi_receive = receive

    async def send(self):
        if hasattr(self.response, "_body"):
            await self._send_start()
            await self.asgi_send({"type": "http.response.body", "body": ensure_bytes(self.response.body)})
            return

        stream = self.response.stream
        client_gone = asyncio.ensure_future(self._client_gone()) if self.asgi_receive else None
        try:
            await self._send_start()
            async with aclosing(aiter(stream)) as chunks:
                while (chunk := await self._next_chunk(chunks, client_gone)) is not _END:
                    if chunk:
                        await self.asgi_send({"type": "http.response.body", "body": chunk, "more_body": True})
            await self.asgi_send({"type": "http.response.body", "body": b""})
        except _ClientGone:
            pass
        finally:
            if client_gone is not None:
                client_gone.cancel()
            await stream.aclose()

    async def _client_gone(self):
        while (await self.asgi_receive())["type"] != "http.disconnect":
            pass

    @staticmethod
    async def _next_chunk(chunks, client_gone: Optional[asyncio.Future]):
        """The next chunk of the body, or :data:`_END`. Raises :class:`_ClientGone` if the client leaves first, after
        interrupting the read, so the upstream is not read any further."""
        if client_gone is None:
            return await anext(chunks, _END)
        read = asyncio.ensure_future(anext(chunks, _END))
        await asyncio.wait({read, client_gone}, return_when=asyncio.FIRST_COMPLETED)
        if read.done():
            return read.result()
        read.cancel()
        with suppress(asyncio.CancelledError):
            await read
        raise _ClientGone()

    async def _send_start(self):
        # set the headers as read only
        self.response._headers = CIMultiDictProxy(self.response._headers)

        # prepare headers for asgi
        headers = tuple((header_bytes(k), header_bytes(v)) for k, v in self.response.headers.items())

        # start the response
        await self.asgi_send(
            {
                "type": "http.response.start",
                "status": self.response.status,
                "headers": headers,
            }
        )
