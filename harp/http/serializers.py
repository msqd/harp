from functools import cached_property
from typing import Protocol
from urllib.parse import urlencode

from harp.http import HttpRequest
from harp.http.typing import BaseMessage


class MessageSerializer(Protocol):
    @property
    def summary(self) -> str:
        return ...

    @property
    def headers(self) -> str:
        return ...

    @property
    def body(self) -> bytes:
        return ...


class HttpRequestSerializer(MessageSerializer):
    """
    Serialize an HTTP request object into string representations for different message parts:

    - summary: the first line of the request message (e.g. "GET / HTTP/1.1")
    - headers: the headers of the request message (e.g. "Host: localhost:4080\nConnection: keep-alive\n...")
    - body: the body of the request message (e.g. b'{"foo": "bar"}')

    The main goal of this serializer is to prepare a message for storage.

    """

    def __init__(self, request: HttpRequest):
        self._request = request

    @cached_property
    def summary(self) -> str:
        query_string = "?" + urlencode(self._request.query) if self._request.query else ""
        return f"{self._request.method} {self._request.path}{query_string} HTTP/1.1"

    @cached_property
    def headers(self) -> str:
        return "\n".join([f"{k}: {v}" for k, v in self._request.headers.items()])

    @cached_property
    def body(self) -> bytes:
        return self._request.body


class LegacyMessageSerializer(MessageSerializer):
    def __init__(self, message):
        self._message = message

    @cached_property
    def summary(self) -> str:
        return self._message.serialized_summary

    @cached_property
    def headers(self) -> str:
        return self._message.serialized_headers

    @cached_property
    def body(self) -> bytes:
        return self._message.serialized_body


def get_serializer_for(message: BaseMessage) -> MessageSerializer:
    if isinstance(message, HttpRequest):
        return HttpRequestSerializer(message)

    from harp.asgi import ASGIResponse

    if isinstance(message, ASGIResponse):
        return LegacyMessageSerializer(message)

    raise ValueError(f"No serializer available for message type: {type(message)}")
