from datetime import UTC, datetime
from functools import cached_property
from itertools import chain

from asgiref.typing import ASGISendCallable
from httpx import codes

from harp.core.asgi.messages.base import AbstractASGIMessage
from harp.core.asgi.messages.requests import ASGIRequest
from harp.utils.bytes import ensure_bytes


class ASGIResponse(AbstractASGIMessage):
    """
    Represents a way to answer an ASGI request, and allows to store the actual response content for future usage.

    """

    kind = "response"
    default_headers = {}

    def __init__(self, request: ASGIRequest, send: ASGISendCallable, *, default_headers=None):
        self._request = request
        self._send = send

        self.status = None
        self.default_headers = default_headers if default_headers is not None else self.default_headers

        self.started = False

        # Keep track of what has been sent, mostly for testing, logging or auditing purposes.
        # The ASGI protocol being async-first, it may be used to send a response in multiple parts.
        self._response = {}

        self.created_at = datetime.now(UTC)

    def snapshot(self):
        return self._response

    async def start(self, *, status=200, headers=None):
        """
        Starts an HTTP response. This is specific to HTTP and may be moved elsewhere later (subclass, protocol specific
        delegate...).

        :param status: The HTTP status code to send.
        :param headers: The HTTP headers to send.

        """
        if self.started:
            raise RuntimeError("HTTP response can only be started once.")

        self.started = True
        self.status = status

        headers = tuple(
            (ensure_bytes(k), ensure_bytes(v))
            for k, v in chain((self.default_headers or {}).items(), (headers or {}).items())
        )
        await self._send(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": headers,
            }
        )

        self._response["status"] = self.status
        self._response["headers"] = headers

    async def body(self, content):
        """
        Sends a body part of the HTTP response. This is specific to HTTP and may be moved elsewhere later (subclass,
        protocol specific delegate...).

        :param content: bytes to send
        """
        if not self.started:
            raise RuntimeError("HTTP response must be started before sending content.")
        content = ensure_bytes(content)
        await self._send(
            {
                "type": "http.response.body",
                "body": content,
            }
        )
        self._response.setdefault("body", b"")
        self._response["body"] += content

    async def close(self):
        """
        Closes the HTTP response. This is specific to HTTP and may be moved elsewhere later (subclass, protocol
        specific delegate...).

        """
        pass

    @cached_property
    def serialized_summary(self):
        """
        Returns a summary of the message as a string (for http requests, command line, for http responses, status line,
        etc.)

        :return: str
        """
        status = self._response["status"]
        reason = codes.get_reason_phrase(status)
        return f"HTTP/1.1 {status} {reason}"

    @cached_property
    def serialized_headers(self):
        headers = self._response["headers"]
        return "\n".join([f"{k.decode('utf-8')}: {v.decode('utf-8')}" for k, v in headers])

    @cached_property
    def serialized_body(self):
        return self._response["body"]
