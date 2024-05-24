from typing import TYPE_CHECKING

from asgiref.typing import ASGISendCallable
from multidict import CIMultiDictProxy

from harp.utils.bytes import ensure_bytes

if TYPE_CHECKING:
    from harp.http import HttpResponse


class HttpResponseAsgiBridge:  # todo protocol HttpResponseBridge
    """Implements the ability of sending our HttpResponse object over the asgi protocol. This is still early impl. and
    it will need to support streaming responses in the future."""

    def __init__(self, response: "HttpResponse", send: ASGISendCallable):
        self.response = response
        self.asgi_send = send

    async def send(self):
        # set the headers as read only
        self.response._headers = CIMultiDictProxy(self.response._headers)

        # prepare headers for asgi
        headers = tuple((ensure_bytes(k), ensure_bytes(v)) for k, v in self.response.headers.items())

        # start the response
        await self.asgi_send(
            {
                "type": "http.response.start",
                "status": self.response.status,
                "headers": headers,
            }
        )

        # send the body
        await self.asgi_send(
            {
                "type": "http.response.body",
                "body": ensure_bytes(self.response.body),
            }
        )
