from functools import cached_property
from urllib.parse import urlencode

from harp.http import HttpRequest


class HttpRequestSerializer:
    def __init__(self, request: HttpRequest):
        self.request = request

    @cached_property
    def summary(self) -> str:
        query_string = "?" + urlencode(self.request.query) if self.request.query else ""
        return f"{self.request.method} {self.request.path}{query_string} HTTP/1.1"

    @cached_property
    def headers(self) -> str:
        return "\n".join([f"{k}: {v}" for k, v in self.request.headers.items()])

    @cached_property
    def body(self) -> bytes:
        return self.request.body
