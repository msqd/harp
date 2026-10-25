from functools import cached_property
from urllib.parse import urlencode

from httpx import codes

from harp.models.redaction import REDACTED, HeaderNames, Redaction
from harp.utils.bytes import header_display

from .errors import HttpError
from .requests import HttpRequest
from .responses import HttpResponse
from .typing import BaseHttpMessage, BaseMessage, MessageSerializer


class BaseHttpMessageSerializer(MessageSerializer):
    """
    Base serializer for HTTP messages.

    """

    def __init__(self, message: BaseHttpMessage, redaction: Redaction | None = None):
        self.wrapped = message
        self.redaction = redaction or Redaction(headers=HeaderNames(), query=set())

    @cached_property
    def summary(self) -> str:
        raise NotImplementedError

    @cached_property
    def headers(self) -> str:
        return "\n".join(
            [
                f"{header_display(k)}: {REDACTED if k.lower() in self.redaction.headers else header_display(v)}"
                for k, v in self.wrapped.headers.items()
            ]
        )

    @cached_property
    def body(self) -> bytes:
        return self.wrapped.body


class HttpRequestSerializer(BaseHttpMessageSerializer):
    """
    Serialize an HTTP request object into string representations for different message parts:

    - summary: the first line of the request message (e.g. "GET / HTTP/1.1")
    - headers: the headers of the request message (e.g. "Host: localhost:4080\nConnection: keep-alive\n...")
    - body: the body of the request message (e.g. b'{"foo": "bar"}')

    The main goal of this serializer is to prepare a request message for storage.

    """

    wrapped: HttpRequest

    @cached_property
    def query_string(self) -> str:
        query = [(k, REDACTED if k in self.redaction.query else v) for k, v in (self.wrapped.query or {}).items()]
        return urlencode(query) if query else ""

    @cached_property
    def summary(self) -> str:
        query = f"?{self.query_string}" if self.query_string else ""
        return f"{self.wrapped.method} {self.wrapped.path}{query} HTTP/1.1"


class HttpResponseSerializer(BaseHttpMessageSerializer):
    """
    Serialize an HTTP response object into string representations for different message parts:

    - summary: the first line of the response message (e.g. "HTTP/1.1 200 OK")
    - headers: the headers of the response message (e.g. "Content-Type: text/plain\nContent-Length: 13\n...")
    - body: the body of the response message (e.g. b'Hello, world!')

    The main goal of this serializer is to prepare a response message for storage.

    """

    wrapped: HttpResponse

    @cached_property
    def summary(self) -> str:
        reason = codes.get_reason_phrase(self.wrapped.status)
        return f"HTTP/1.1 {self.wrapped.status} {reason}"


class HttpErrorSerializer(BaseHttpMessageSerializer):
    """
    Serialize an HTTP error object into string representations for different message parts:

    - summary: the error message
    - headers: empty
    - body: stack trace (xxx this may change, maybe too much info and too much internal)

    The main goal of this serializer is to prepare an error message for storage.

    """

    wrapped: HttpError

    @cached_property
    def summary(self) -> str:
        return self.wrapped.message


def get_serializer_for(message: BaseMessage, redaction: Redaction | None = None) -> MessageSerializer:
    if isinstance(message, HttpRequest):
        return HttpRequestSerializer(message, redaction)

    if isinstance(message, HttpResponse):
        return HttpResponseSerializer(message, redaction)

    if isinstance(message, HttpError):
        return HttpErrorSerializer(message, redaction)

    raise ValueError(f"No serializer available for message type: {type(message)}")
