import time
from typing import Any, Dict, Optional
from base64 import b64encode
from urllib.parse import unquote, urlparse

from httpx import AsyncClient, Request, Response

from harp import __parsed_version__
from harp.http import HttpRequest
from harp.http.utils import hop_by_hop_names
from harp.utils.bytes import HEADER_ENCODING, header_bytes


def strip_credentials(url: str) -> str:
    """The url without its ``user:password@`` part, safe to log and record."""
    parsed_url = urlparse(url)
    return parsed_url._replace(netloc=parsed_url.netloc.rpartition("@")[2]).geturl()


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
        response.headers.encoding = HEADER_ENCODING  # obs-text must read back as the bytes it was

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
        request.headers["host"] = parsed_url.netloc.rpartition("@")[2]
        if self.user_agent:
            request.headers["user-agent"] = self.user_agent
        dropped = hop_by_hop_names(request.headers)
        headers = [(name, value) for name, value in request.headers.items() if name.lower() not in dropped]
        # Endpoint credentials are a fallback: any Authorization already on the request wins. Added to the
        # outgoing list only, so they never land on the recorded request.
        if parsed_url.username is not None and "authorization" not in request.headers:
            credentials = f"{unquote(parsed_url.username)}:{unquote(parsed_url.password or '')}"
            headers.append(("authorization", "Basic " + b64encode(credentials.encode()).decode()))
        return headers

    def _build_request(self, request: HttpRequest, url: str) -> Request:
        """
        Build the HTTP request.

        :param request: The HttpRequest object.
        :param url: The URL to which the request is sent.
        :return: The built HTTP request.
        """
        headers = self._get_updated_headers(request, url=url)

        # Credentials travel in the Authorization header built above. Left in the url, httpx would override
        # that header with its own and the url would be recorded with the secret.
        remote_request = self.http_client.build_request(
            request.method,
            strip_credentials(url),
            headers=[(header_bytes(name), header_bytes(value)) for name, value in headers],
            content=request.body,
            extensions={"harp": {**self.extensions}},
        )

        request.extensions["remote_method"] = remote_request.method
        request.extensions["remote_url"] = str(remote_request.url)
        return remote_request
