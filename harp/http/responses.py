import orjson
from multidict import CIMultiDict

from harp.utils.bytes import ensure_bytes

from .typing import BaseHttpMessage


class HttpResponse(BaseHttpMessage):
    kind = "response"

    def __init__(self, body: bytes | str, /, *, status: int = 200, headers: dict = None, content_type=None):
        super().__init__()

        self._body = ensure_bytes(body)
        self._status = int(status)
        self._headers = CIMultiDict(headers or {})

        if content_type:
            self._headers["content-type"] = content_type

    @property
    def body(self) -> bytes:
        return self._body

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> CIMultiDict:
        return self._headers

    @property
    def content_type(self) -> str:
        return self._headers.get("content-type", "text/plain")


class JsonHttpResponse(HttpResponse):
    def __init__(self, body: dict, /, *, status: int = 200, headers: dict = None):
        super().__init__(orjson.dumps(body), status=status, headers=headers, content_type="application/json")


class AlreadyHandledHttpResponse(HttpResponse):
    def __init__(self):
        super().__init__(b"")
