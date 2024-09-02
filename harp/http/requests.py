import binascii
from base64 import b64decode
from typing import Optional

from httpx import AsyncByteStream, ByteStream
from multidict import CIMultiDict

from .typing import BaseHttpMessage, HttpRequestBridge
from .utils.cookies import parse_cookie


class HttpRequest(BaseHttpMessage):
    kind = "request"

    def __init__(
        self,
        impl: Optional[HttpRequestBridge] = None,
        *,
        extensions: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(extensions=extensions)

        if impl is None:
            from .tests.stubs import HttpRequestStubBridge

            impl = HttpRequestStubBridge(**kwargs)
        else:
            if len(kwargs) > 0:
                raise ValueError("Cannot pass both an implementation and non-explicit keyword arguments.")

        self._impl = impl

        # Initialize properties from the implementation bridge
        self.method = self._impl.get_method()
        self.path = self._impl.get_path()
        self.query = self._impl.get_query()
        self.server_ipaddr = self._impl.get_server_ipaddr()
        self.server_port = self._impl.get_server_port()
        self._headers = self._impl.get_headers()
        self._stream = self._impl.get_stream()

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, stream: AsyncByteStream):
        self._stream = stream
        if hasattr(self, "_body"):
            delattr(self, "_body")

    @property
    def headers(self) -> CIMultiDict:
        return self._headers

    @headers.setter
    def headers(self, headers):
        self._headers = CIMultiDict(headers)

    @property
    def cookies(self) -> dict:
        cookies = {}
        for header in self.headers.getall("cookie", []):
            cookies.update(parse_cookie(header))
        return cookies

    @property
    def basic_auth(self) -> tuple[str, str] | None:
        """Parse and returns basic auth from headers."""
        for header in self.headers.getall("authorization", []):
            try:
                _type, _auth = header.split(" ", 1)
            except ValueError:
                continue

            if _type.lower() == "basic":
                try:
                    user, passwd = b64decode(_auth).decode("utf-8").split(":", 1)
                except (binascii.Error, ValueError):
                    continue

                return user, passwd

    @property
    def body(self) -> bytes:
        """Returns the previously read body of the request. Raises a RuntimeError if the body has not been read yet,
        you must await the `read()` asynchronous method first, which cannot be done here because properties are
        synchronous, so we let the user explicitely call it before."""
        if not hasattr(self, "_body"):
            raise RuntimeError("Request body has not been read yet, please await `read()` first.")
        return self._body

    async def aread(self) -> bytes:
        """Read all chunks from request. We may want to be able to read partial body later, but for now it's all or
        nothing. This method does nothing if the body has already been read."""
        if not hasattr(self, "_body"):
            self._body = b"".join([part async for part in self._stream])
            # self.headers["content-length"] = str(len(self.body))
        if not isinstance(self._stream, ByteStream):
            self._stream = ByteStream(self._body)
        return self.body

    def __str__(self):
        return f"{self.method} {self.path}"
