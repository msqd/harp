import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from httpx import AsyncClient, Request, Response

from harp import __parsed_version__
from harp.http import HttpRequest

#: Header fields that describe the connection a message arrived on rather than the message itself,
#: and so must not be passed on to the next one (RFC 9110 §7.6.1). ``transfer-encoding`` and
#: ``content-length`` are here for a second reason: they describe the framing of a body HARP has
#: already read and is re-sending itself, so the client's claim about them is not ours to forward.
#: Doing so lets a client hand the upstream a message carrying both, which RFC 9112 §6.1 forbids an
#: intermediary from relaying because recipients disagree about which one wins.
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "content-length",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


class HttpClientProxyAdapter:
    user_agent: Optional[str] = None
    """User agent to use when proxying requests (will default to harp/<version>)."""

    def __init__(self, http_client: AsyncClient, *, extensions: Optional[Dict[str, Any]] = None):
        self.http_client = http_client
        self.user_agent = self.user_agent or self._get_default_user_agent()
        self.extensions = extensions or {}

    async def send(self, request: HttpRequest, url: str) -> Response:
        """
        Send the HTTP request using the provided URL.

        :param request: The HttpRequest object to be sent.
        :param url: The URL to which the request is sent.
        :return: The HTTP response received.
        """
        request = self._build_request(request, url)
        response = await self.http_client.send(request)

        # Add cache debugging headers if caching is being used
        if response.extensions.get("hishel_from_cache"):
            response.headers["X-Cache"] = "HIT"
            # Add Age header for cached responses
            created_at = response.extensions.get("hishel_created_at")
            if created_at is not None:
                age = int(time.time() - created_at)
                response.headers["Age"] = str(age)
        elif "hishel_from_cache" in response.extensions:
            # hishel is present but response is not from cache
            response.headers["X-Cache"] = "MISS"

        return response

    def _get_default_user_agent(self) -> str:
        """
        Get the default user agent string.

        :return: The default user agent string.
        """
        try:
            return f"harp/{__parsed_version__.major}.{__parsed_version__.minor}"
        except AttributeError:
            return "harp"

    def _get_updated_headers(self, request: HttpRequest, *, url: str) -> list:
        """
        Update the headers for the request.

        :param request: The HttpRequest object.
        :param url: The URL to which the request is sent.
        :return: A list of updated headers.
        """
        parsed_url = urlparse(url)
        request.headers["host"] = parsed_url.netloc
        if self.user_agent:
            request.headers["user-agent"] = self.user_agent
        # `Connection` names further fields that are also specific to the incoming connection.
        named_by_connection = {
            name.strip().lower() for name in request.headers.get("connection", "").split(",") if name.strip()
        }
        dropped = HOP_BY_HOP_HEADERS | named_by_connection
        return [(name, value) for name, value in request.headers.items() if name.lower() not in dropped]

    def _build_request(self, request: HttpRequest, url: str) -> Request:
        """
        Build the HTTP request.

        :param request: The HttpRequest object.
        :param url: The URL to which the request is sent.
        :return: The built HTTP request.
        """
        headers = self._get_updated_headers(request, url=url)

        remote_request = self.http_client.build_request(
            request.method,
            url,
            headers=headers,
            content=request.body,
            extensions={"harp": {**self.extensions}},
        )

        request.extensions["remote_method"] = remote_request.method
        request.extensions["remote_url"] = str(remote_request.url)
        return remote_request
