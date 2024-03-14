from datetime import UTC, datetime
from functools import cached_property

from asgiref.typing import ASGISendCallable
from httpx import codes
from multidict import CIMultiDict, CIMultiDictProxy

from harp.asgi.messages.requests import ASGIRequest
from harp.utils.bytes import ensure_bytes


class ASGIResponse:
    """
    Represents a way to answer an ASGI request, and allows to store the actual response content for future usage.

    """

    kind = "response"
    default_headers = {}

    def __init__(self, request: ASGIRequest, send: ASGISendCallable):
        # todo no request needed in response ?
        self._request = request
        self._send = send

        self.status = None
        self.headers = CIMultiDict()

        self.started = False

        # Keep track of what has been sent, mostly for testing, logging or auditing purposes.
        # The ASGI protocol being async-first, it may be used to send a response in multiple parts.
        self.__deprecated_data_snapshot_for_early_developments = {}

        self.created_at = datetime.now(UTC)

    def snapshot(self):
        return self.__deprecated_data_snapshot_for_early_developments

    async def start(self, status=200):
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

        # headers are now readonly
        self.headers = CIMultiDictProxy(self.headers)

        headers = tuple((ensure_bytes(k), ensure_bytes(v)) for k, v in self.headers.items())
        await self._send(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": headers,
            }
        )

        self.__deprecated_data_snapshot_for_early_developments["status"] = self.status
        self.__deprecated_data_snapshot_for_early_developments["headers"] = headers

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
        self.__deprecated_data_snapshot_for_early_developments.setdefault("body", b"")
        self.__deprecated_data_snapshot_for_early_developments["body"] += content

    async def close(self):
        """
        Closes the HTTP response. This is specific to HTTP and may be moved elsewhere later (subclass, protocol
        specific delegate...).

        """
        pass

    @cached_property
    def serialized_summary(self) -> str:
        """
        Returns a summary of the message as a string (for http requests, command line, for http responses, status line,
        etc.)

        :return: str
        """
        status = self.__deprecated_data_snapshot_for_early_developments["status"]
        reason = codes.get_reason_phrase(status)
        return f"HTTP/1.1 {status} {reason}"

    @property
    def serialized_headers(self) -> str:
        return "\n".join([f"{k}: {v}" for k, v in self.headers.items()])

    @cached_property
    def serialized_body(self) -> bytes:
        return self.__deprecated_data_snapshot_for_early_developments["body"]

    async def read(self) -> list[bytes]:
        return []
