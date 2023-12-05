from functools import cached_property


class ASGIRequest:
    def __init__(self, scope, receive):
        self._scope = scope
        self._body = b""
        self._receive = receive

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
        return self._scope.get("headers", [])

    @cached_property
    def serialized_summary(self):
        return f"{self.method} {self.path}{('?'+self.query_string if self.query_string else '')} HTTP/1.1"

    @cached_property
    def serialized_headers(self):
        return "\n".join([f"{k.decode('utf-8')}: {v.decode('utf-8')}" for k, v in self.headers])

    @cached_property
    def serialized_body(self):
        return self._body

    def serialize(self):
        return {
            "type": self.type,
            "subtype": "request",
            "method": self.method,
            "path": self.path,
            "query_string": self.query_string,
            "headers": self.headers,
        }
