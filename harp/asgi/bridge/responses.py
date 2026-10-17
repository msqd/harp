from contextlib import aclosing
from typing import TYPE_CHECKING

from asgiref.typing import ASGISendCallable
from multidict import CIMultiDictProxy

from harp.utils.bytes import ensure_bytes, header_bytes

if TYPE_CHECKING:
    from harp.http import HttpResponse


class HttpResponseAsgiBridge:  # todo protocol HttpResponseBridge
    """Implements the ability of sending our HttpResponse object over the asgi protocol.

    A body held in memory goes out in one message. A streamed body goes out chunk by chunk, each chunk sent before the
    next one is read, and its stream is closed once sent or once the client is gone."""

    def __init__(self, response: "HttpResponse", send: ASGISendCallable):
        self.response = response
        self.asgi_send = send

    async def send(self):
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

        if hasattr(self.response, "_body"):
            await self.asgi_send({"type": "http.response.body", "body": ensure_bytes(self.response.body)})
        else:
            await self._send_stream()

    async def _send_stream(self):
        stream = self.response.stream
        try:
            async with aclosing(aiter(stream)) as chunks:
                async for chunk in chunks:
                    if chunk:
                        await self.asgi_send({"type": "http.response.body", "body": chunk, "more_body": True})
            await self.asgi_send({"type": "http.response.body", "body": b""})
        finally:
            await stream.aclose()
