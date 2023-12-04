from itertools import chain

from asgiref.typing import ASGISendCallable

from harp.core.asgi.requests import ASGIRequest
from harp.utils.bytes import ensure_bytes


class ASGIResponder:
    default_headers = {"x-powered-by": "harp"}

    def __init__(self, request: ASGIRequest, send: ASGISendCallable, *, default_headers=None):
        self._request = request
        self._send = send

        self.status = None
        self.default_headers = default_headers if default_headers is not None else self.default_headers

        self.started = False

        # helper to be able to read what this responder already sent
        self._response = {}

    async def start(self, *, status=200, headers=None):
        if self.started:
            raise RuntimeError("Responder can only be started once.")

        self.started = True
        self.status = status

        headers = tuple(
            (ensure_bytes(k), ensure_bytes(v))
            for k, v in chain((self.default_headers or {}).items(), (headers or {}).items())
        )
        await self._send(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": headers,
            }
        )

        self._response["status"] = self.status
        self._response["headers"] = headers

    async def body(self, content):
        if not self.started:
            raise RuntimeError("Responder must be started before sending content.")
        content = ensure_bytes(content)
        await self._send(
            {
                "type": "http.response.body",
                "body": content,
            }
        )
        self._response.setdefault("body", b"")
        self._response["body"] += content

    async def close(self):
        pass
