from typing import AsyncIterator, Protocol

from multidict import CIMultiDict, MultiDict


class HttpRequestBridge(Protocol):
    """
    The HttpRequestBridge protocol defines the methods required by the HttpRequest object for it to attach to a real
    implementation, such as WSGI, ASGI, ...
    """

    def get_server_ipaddr(self) -> str: ...

    def get_server_port(self) -> int: ...

    def get_method(self) -> str: ...

    def get_path(self) -> str: ...

    def get_query(self) -> MultiDict: ...

    def get_headers(self) -> CIMultiDict: ...

    async def read(self) -> bytes: ...

    async def stream(self) -> AsyncIterator[bytes]:
        yield ...


class HttpResponseBridge(Protocol):
    """
    The HttpResponseBridge protocol defines the necessary methods to actually send an HttpResponse through a real
    channel.
    """
