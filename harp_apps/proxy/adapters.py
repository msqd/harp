import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from httpx import AsyncClient, Request, Response

from harp import __parsed_version__
from harp.http import HttpRequest

logger = logging.getLogger(__name__)


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
        return await self.http_client.send(request)

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
        return list(request.headers.items())

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
