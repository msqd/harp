from datetime import UTC, datetime
from functools import cached_property
from urllib.parse import parse_qsl

from multidict import CIMultiDict, CIMultiDictProxy

from harp import get_logger

logger = get_logger(__name__)


class ASGIRequest:
    """

    The `ASGIRequest` class represents an ASGI request object.
    """

    kind = "request"

    def __init__(self, scope, receive):
        """
        :param receive:
        """
        self._scope = scope
        self._body = b""
        self._receive = receive
        self.created_at = datetime.now(UTC)

        self._context = {}

    @property
    def context(self) -> dict:
        """Contextual data for this request's lifecycle. Example usage: authentication bagage."""
        return self._context

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
        """DEPRECATED: use request.query instead."""
        return self._scope.get("query_string", b"").decode("utf-8")

    @cached_property
    def query(self):
        return CIMultiDictProxy(CIMultiDict(parse_qsl(self._scope.get("query_string", b"").decode("utf-8"))))

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
    def serialized_body(self):
        return self._body
