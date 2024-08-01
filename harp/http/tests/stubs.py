from typing import AsyncIterator, Mapping
from urllib.parse import parse_qsl

from httpx import AsyncByteStream
from multidict import CIMultiDict, MultiDict

from harp.http import HttpRequestBridge


class AsyncByteStreamFromBody(AsyncByteStream):
    def __init__(self, body) -> None:
        self._body = body

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._body:
            yield chunk

    async def aclose(self) -> None:
        pass


class HttpRequestStubBridge(HttpRequestBridge):
    def __init__(
        self,
        /,
        *,
        server_ipaddr: str = "127.0.0.1",
        server_port: int = 80,
        method: str = "GET",
        path: str = "/",
        query: Mapping | str = None,
        headers: Mapping = None,
        body: bytes | list | None = None,
    ):
        self._server_ipaddr = server_ipaddr
        self._server_port = server_port
        self._method = str(method).upper()
        self._path = path

        if isinstance(body, bytes):
            self._body = [body]
        elif isinstance(body, list):
            self._body = body
        else:
            self._body = []
        self._closed = False

        if isinstance(query, str):
            query = parse_qsl(query)
        self._query = MultiDict(query or {})
        self._headers = CIMultiDict(headers or {})

    def get_server_ipaddr(self) -> str:
        return self._server_ipaddr

    def get_server_port(self) -> int:
        return self._server_port

    def get_method(self) -> str:
        return self._method

    def get_path(self) -> str:
        return self._path

    def get_query(self) -> MultiDict:
        return self._query

    def get_headers(self) -> CIMultiDict:
        return self._headers

    def get_stream(self) -> AsyncByteStream:
        return AsyncByteStreamFromBody(self._body)

    async def aread(self) -> bytes:
        return b"".join(self._body)
