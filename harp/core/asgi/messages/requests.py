from datetime import UTC, datetime
from functools import cached_property
from http.cookies import SimpleCookie

from multidict import CIMultiDict, CIMultiDictProxy

from harp import get_logger
from harp.core.asgi.messages.base import AbstractASGIMessage

logger = get_logger(__name__)


class ASGIRequest(AbstractASGIMessage):
    kind = "request"

    def __init__(self, scope, receive):
        """
        :param scope: see https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
        :param receive:
        """
        self._scope = scope
        self._body = b""
        self._receive = receive
        self.created_at = datetime.now(UTC)

    async def receive(self):
        return await self._receive()

    @cached_property
    def scope(self):
        return self._scope

    @cached_property
    def type(self):
        return self._scope.get("type", None)

    @cached_property
    def port(self):
        return self._scope.get("server", [None, None])[1]

    @cached_property
    def method(self):
        return self._scope.get("method", None)

    @cached_property
    def path(self):
        if "raw_path" in self._scope:
            return self._scope["raw_path"].decode("utf-8")
        return self._scope.get("path", "/")

    @cached_property
    def query_string(self):
        return self._scope.get("query_string", b"").decode("utf-8")

    @cached_property
    def headers(self):
        headers = CIMultiDict()
        for name, value in self._scope.get("headers", []):
            headers.add(name.decode("utf-8"), value.decode("utf-8"))
        return CIMultiDictProxy(headers)

    @cached_property
    def serialized_summary(self):
        return f"{self.method} {self.path}{('?' + self.query_string if self.query_string else '')} HTTP/1.1"

    @cached_property
    def serialized_headers(self):
        return "\n".join([f"{k}: {v}" for k, v in self.headers.items()])

    @cached_property
    def cookies(self):
        """Parse cookies from headers."""
        cookies = SimpleCookie()
        for header in self.headers.getall("cookie", []):
            logger.info('Parsing cookie header "%s"', header)
            cookies.load(header)
        return cookies

    @cached_property
    def serialized_body(self):
        return self._body
