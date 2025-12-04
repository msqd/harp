import orjson
from httpx import AsyncByteStream, ByteStream, codes
from multidict import CIMultiDict
from typing import Optional

from harp.utils.bytes import ensure_bytes
from .typing import BaseHttpMessage


class HttpResponse(BaseHttpMessage):
    kind = "response"

    def __init__(
        self,
        body: bytes | str,
        /,
        *,
        status: int = 200,
        headers: Optional[dict] = None,
        content_type=None,
        extensions: Optional[dict] = None,
    ):
        super().__init__(extensions=extensions)

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
    def reason_phrase(self) -> str:
        try:
            reason_phrase = self.extensions["reason_phrase"]
        except KeyError:
            return codes.get_reason_phrase(self.status)

        if isinstance(reason_phrase, bytes):
            return reason_phrase.decode("ascii", errors="ignore")
        return reason_phrase

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
        from harp.views.json import serialize

        super().__init__(
            serialize(body),
            status=status,
            headers=headers,
            content_type="application/json",
        )

    def asdict(self):
        return orjson.loads(self.body)


class AlreadyHandledHttpResponse(HttpResponse):
    def __init__(self):
        super().__init__(b"")


class RedirectHttpResponse(HttpResponse):
    def __init__(self, location: str, /, *, status: int = 302, headers: dict = None):
        if headers is None:
            headers = {}
        headers["Location"] = location
        super().__init__(b"", status=status, headers=headers)
