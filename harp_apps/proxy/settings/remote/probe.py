from base64 import b64encode
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from urllib.parse import unquote, urljoin, urlparse

import httpx
from pydantic import Field
from pyheck import shouty_snake

from harp import get_logger
from harp.config import Configurable, Secret, Stateful
from harp_apps.proxy.adapters import strip_credentials

if TYPE_CHECKING:
    from harp_apps.proxy.settings.remote.endpoint import RemoteEndpoint

logger = get_logger(__name__)


class RemoteProbeSettings(Configurable):
    """
    A ``HttpProbe`` is a health check that can be used to check the health of a remote's endpoints. It is used as the
    configuration parser for ``proxy.endpoints[].remote.probe`` settings.

    .. code-block:: yaml

        type: http
        method: GET
        path: /health
        headers:
          x-purpose: "health probe"
        timeout: 5.0
    """

    method: str = "GET"
    path: str = "/"
    headers: dict[str, Secret] = Field(default_factory=dict)
    interval: float = 10.0
    timeout: float = 10.0
    verify: bool = True


class RemoteProbe(Stateful[RemoteProbeSettings]):
    """Stateful version of a probe definition."""

    @asynccontextmanager
    async def async_client(self):
        async with httpx.AsyncClient(verify=self.settings.verify) as client:
            yield client

    def _get_headers(self, url: str) -> dict:
        """Probe headers, with the endpoint credentials as a Basic fallback (never in the url, so never logged)."""
        headers = {name: value.get_secret_value() for name, value in self.settings.headers.items()}
        parsed_url = urlparse(url)
        if parsed_url.username is not None and "authorization" not in {name.lower() for name in headers}:
            credentials = f"{unquote(parsed_url.username)}:{unquote(parsed_url.password or '')}"
            headers["Authorization"] = "Basic " + b64encode(credentials.encode()).decode()
        return headers

    async def check(self, client: httpx.AsyncClient, endpoint: "RemoteEndpoint"):
        full_url = urljoin(str(endpoint.settings.url), self.settings.path)
        probe_url = strip_credentials(full_url)
        headers = self._get_headers(full_url)
        response = None
        try:
            response = await client.request(
                self.settings.method,
                probe_url,
                headers=headers,
                timeout=float(self.settings.timeout),
            )
            if 200 <= response.status_code < 400:
                return endpoint.success()
            else:
                failure = f"PROBE_HTTP_{response.status_code}"
                logger.warning(f"Probe failure: {probe_url} -> {failure}")
                return endpoint.failure(failure)
        except Exception as exc:
            failure = "PROBE_" + shouty_snake(type(exc).__name__)
            logger.error(f"Probe failure: {probe_url} -> {failure}")
            return endpoint.failure(failure)
        finally:
            if response:
                logger.debug(f"Probe request: {probe_url} -> {response.status_code}")
