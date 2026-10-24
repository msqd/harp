from typing import Optional
from urllib.parse import parse_qsl

from asgiref.typing import ASGIReceiveCallable, HTTPScope
from httpx import AsyncByteStream
from multidict import CIMultiDict, MultiDict

from harp.asgi.bridge.streams import AsyncStreamFromAsgiReceive
from harp.http import HttpRequestBridge, RejectedRequest
from harp.utils.bytes import header_str

_default_host = (None, None)


class HttpRequestAsgiBridge(HttpRequestBridge):
    """Actually implements the getters required by HttpRequest using the asgi scope and receive callable. It is still
    an early implementation and will need to support streaming requests in the future.
    """

    def __init__(self, scope: HTTPScope, receive: ASGIReceiveCallable):
        """
        :param scope: see https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
        :param receive:
        """
        self.asgi_scope = scope
        self.asgi_receive = receive

        self._closed = False

    def get_server_ipaddr(self) -> Optional[str]:
        """Get the server IP address from asgi scope."""
        try:
            return (self.asgi_scope.get("server", _default_host) or _default_host)[0]
        except IndexError:
            return None

    def get_server_port(self) -> Optional[int]:
        """Get the server port from asgi scope."""
        try:
            return (self.asgi_scope.get("server", _default_host) or _default_host)[1]
        except IndexError:
            return None

    def get_method(self) -> str:
        """Get the HTTP method from asgi scope."""
        return self.asgi_scope.get("method", None)

    def get_path(self) -> str:
        """Get the HTTP path from asgi scope (/foo/bar), without the query string part."""
        if "raw_path" in self.asgi_scope:
            try:
                return self.asgi_scope["raw_path"].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RejectedRequest("Request path is not valid UTF-8.", status=400) from exc
        return self.asgi_scope.get("path", "/")

    def get_query(self) -> MultiDict:
        """Get the query string from asgi scope, as a multidict."""
        try:
            query_string = self.asgi_scope.get("query_string", b"").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RejectedRequest("Request query string is not valid UTF-8.", status=400) from exc
        return MultiDict(parse_qsl(query_string, keep_blank_values=True))

    def get_headers(self) -> CIMultiDict:
        """Get the headers from asgi scope, as a case-insensitive multidict."""
        headers = CIMultiDict()
        for name, value in self.asgi_scope.get("headers", []):
            headers.add(header_str(name), header_str(value))
        if "content-length" in headers and "transfer-encoding" in headers:
            raise RejectedRequest(
                "Request has both Content-Length and Transfer-Encoding.",
                status=400,
                headers={"Connection": "close"},
            )
        return headers

    def get_stream(self) -> AsyncByteStream:
        """Get the request body stream from asgi receive callable."""
        return AsyncStreamFromAsgiReceive(self.asgi_receive)
