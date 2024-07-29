import orjson
from httpx import AsyncByteStream
from multidict import CIMultiDict

from harp.utils.bytes import ensure_bytes

from .streams import ByteStream
from .typing import BaseHttpMessage


class HttpResponse(BaseHttpMessage):
    kind = "response"

    def __init__(self, body: bytes | str, /, *, status: int = 200, headers: dict = None, content_type=None):
        super().__init__()

        self._body = ensure_bytes(body)
        self._status = int(status)
        self._headers = CIMultiDict(headers or {})
        self._stream: AsyncByteStream = ByteStream(self._body)

        if content_type:
            self._headers["content-type"] = content_type

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, stream):
        self._stream = stream
        if hasattr(self, "_body"):
            delattr(self, "_body")

    @property
    def body(self) -> bytes:
        if not hasattr(self, "_body"):
            raise RuntimeError("The 'body' attribute is not available, please await `aread()` first.")
        return self._body

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> CIMultiDict:
        return self._headers

    @headers.setter
    def headers(self, headers: CIMultiDict):
        self._headers = CIMultiDict(headers)

    @property
    def content_type(self) -> str:
        return self._headers.get("content-type", "text/plain")

    async def aread(self):
        if not hasattr(self, "_body"):
            self._body = b"".join([part async for part in self._stream])
        if not isinstance(self._stream, ByteStream):
            self._stream = ByteStream(self._body)
        return self.body


class JsonHttpResponse(HttpResponse):
    def __init__(self, body: dict, /, *, status: int = 200, headers: dict = None):
        super().__init__(orjson.dumps(body), status=status, headers=headers, content_type="application/json")


class AlreadyHandledHttpResponse(HttpResponse):
    def __init__(self):
        super().__init__(b"")
