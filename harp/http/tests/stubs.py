from typing import AsyncIterator, Mapping
from urllib.parse import parse_qsl

from multidict import CIMultiDict, MultiDict

from harp.http import HttpRequestBridge


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
        self._method = method
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

    async def stream(self) -> AsyncIterator[bytes]:
        if self._closed:
            raise RuntimeError("Request body has already been read.")

        for chunk in self._body:
            yield chunk

        self._closed = True
