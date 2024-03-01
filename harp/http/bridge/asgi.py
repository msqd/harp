from typing import Optional
from urllib.parse import parse_qsl

from asgiref.typing import ASGIReceiveCallable, HTTPScope
from multidict import CIMultiDict, MultiDict

from harp.http.typing import HttpRequestBridge

_default_host = (None, None)


class HttpRequestAsgiBridge(HttpRequestBridge):
    """Actually implements the getters required by HttpRequest using the asgi scope and receive callable."""

    def __init__(self, scope: HTTPScope, receive: ASGIReceiveCallable):
        """
        :param scope: see https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
        :param receive:
        """
        self.scope = scope
        self.receive = receive

    def get_server_ipaddr(self) -> Optional[str]:
        """Get the server IP address from asgi scope."""
        try:
            return (self.scope.get("server", _default_host) or _default_host)[0]
        except IndexError:
            return None

    def get_server_port(self) -> Optional[int]:
        """Get the server port from asgi scope."""
        try:
            return (self.scope.get("server", _default_host) or _default_host)[1]
        except IndexError:
            return None

    def get_method(self) -> str:
        """Get the HTTP method from asgi scope."""
        return self.scope.get("method", None)

    def get_path(self) -> str:
        """Get the HTTP path from asgi scope (/foo/bar), without the query string part."""
        if "raw_path" in self.scope:
            return self.scope["raw_path"].decode("utf-8")
        return self.scope.get("path", "/")

    def get_query(self) -> MultiDict:
        """Get the query string from asgi scope, as a multidict."""
        return MultiDict(parse_qsl(self.scope.get("query_string", b"").decode("utf-8")))

    def get_headers(self) -> CIMultiDict:
        """Get the headers from asgi scope, as a case-insensitive multidict."""
        headers = CIMultiDict()
        for name, value in self.scope.get("headers", []):
            headers.add(name.decode("utf-8"), value.decode("utf-8"))
        return headers
