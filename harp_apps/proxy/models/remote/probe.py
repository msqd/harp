from copy import copy
from functools import cached_property
from urllib.parse import urljoin

import httpx
from pyheck import shouty_snake

from harp import get_logger
from harp.config import StatefulConfigurableWrapper
from harp_apps.proxy.settings.remote import RemoteProbeSettings

from .endpoint import RemoteEndpoint

logger = get_logger(__name__)


class RemoteProbe(StatefulConfigurableWrapper[RemoteProbeSettings]):
    @cached_property
    def headers(self):
        return copy(self.settings.headers)

    async def check(self, client: httpx.AsyncClient, endpoint: RemoteEndpoint):
        probe_url = urljoin(str(endpoint.url), self.path)
        failure = None
        try:
            response = await client.request(
                self.method,
                probe_url,
                headers=self.headers,
                timeout=float(self.timeout),
            )
            if 200 <= response.status_code < 400:
                return endpoint.success()
            else:
                failure = f"HTTP_{response.status_code}"
                return endpoint.failure(failure)
        except Exception as exc:
            failure = shouty_snake(type(exc).__name__)
            return endpoint.failure(failure)
        finally:
            if failure:
                logger.info(f"Probe failure: {endpoint.url} -> {failure}")


"""
    def _asdict(self, /, *, secure=True):
        return {
            "type": "http",
            "method": self.method,
            "path": self.path,
            **({"headers": self.headers} if self.headers else {}),
            **({"timeout": self.timeout} if self.timeout != type(self).timeout else {}),
            **({"interval": self.interval} if self.interval != type(self).interval else {}),
            **({"verify": self.verify} if self.verify != type(self).verify else {}),
        }

"""
