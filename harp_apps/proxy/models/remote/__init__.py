import asyncio
import warnings
from collections import deque
from functools import cached_property
from typing import Mapping

import httpx

from harp import get_logger
from harp.config import StatefulConfigurableWrapper
from harp.utils.urls import normalize_url
from harp_apps.proxy.constants import CHECKING, DEFAULT_POOL, DOWN, FALLBACK_POOL, UP
from harp_apps.proxy.settings.remote import RemoteSettings

from .endpoint import RemoteEndpoint
from .probe import RemoteProbe

logger = get_logger(__name__)


class Remote(StatefulConfigurableWrapper[RemoteSettings]):
    #: Current pool deque contains the list of available URLs, from least recently used to most recently used. It will
    #: be rotated on each request to implement a naive round-robin strategy.
    current_pool: deque[RemoteEndpoint]

    #: Remote endpoints with current status.
    endpoints: Mapping[str, RemoteEndpoint]

    def __init__(self, settings: RemoteSettings):
        super().__init__(settings)

        self.endpoints = {
            normalize_url(str(endpoint.url)): RemoteEndpoint(endpoint) for endpoint in (settings.endpoints or ())
        }
        self.current_pool = deque()

        self.refresh()

    def __getitem__(self, url: str) -> RemoteEndpoint:
        return self.endpoints[normalize_url(url)]

    @cached_property
    def probe(self):
        return RemoteProbe(self.settings.probe)

    def refresh(self):
        """Recompute the current pool of endpoints."""
        refreshed: deque[RemoteEndpoint] = deque()
        for endpoint in self.endpoints.values():
            if DEFAULT_POOL in endpoint.pools and endpoint.status >= CHECKING:
                refreshed.append(endpoint)

        if len(refreshed) < self.min_pool_size:
            for endpoint in self.endpoints.values():
                if FALLBACK_POOL in endpoint.pools and endpoint.status >= CHECKING:
                    self.current_pool_name = FALLBACK_POOL
                    refreshed.append(endpoint)
        else:
            self.current_pool_name = DEFAULT_POOL

        self.current_pool = refreshed

    def get_url(self) -> str:
        """Get next candidate url from the current pool, then rotate."""
        try:
            return str(self.current_pool[0].url)
        except IndexError as exc:
            raise IndexError("No available URLs for remote.") from exc

        finally:
            self.current_pool.rotate(-1)

    def notify_url_status(self, url, status):
        """
        Take into account a http status code to update the status of the url. Behaviour differs depending on the
        instance configuration (some considers 5xx as down, some ignores non-network errors).
        """
        if ("http_5xx" in self.break_on and 500 <= status < 600) or (
            "http_4xx" in self.break_on and 400 <= status < 500
        ):
            if self[url].failure(f"HTTP_{status}"):
                self.refresh()

    def set_down(self, url):
        old_status = self[url].status

        self[url].status = DOWN

        if old_status >= DOWN:

            async def delayed_set_checking():
                await asyncio.sleep(self.delay_for_checking_down_endpoints)
                if self[url].status == DOWN:
                    self.set_checking(url)
                del self[url].delayed_set_checking

            try:
                self[url].delayed_set_checking = asyncio.create_task(delayed_set_checking())
            except RuntimeError as exc:
                warnings.warn(f"Failed to schedule delayed checking state: {exc}")

        self.refresh()

    def set_checking(self, url):
        self[url].status = CHECKING
        self.refresh()

    def set_up(self, url):
        self[url].status = UP
        self.refresh()

    async def check(self):
        """Uses the probe (luke), to check the health of each urls. It is also done on fallback and inactive urls, to
        ensure that they are ready in case we need them."""
        if self.probe is None:
            return

        state_changed = False

        async with httpx.AsyncClient(verify=self.probe.verify) as client:
            for url in self.endpoints.values():
                url_state_changed = await self.probe.check(client, url)
                state_changed |= url_state_changed

        if state_changed:
            self.refresh()

    async def check_forever(self):
        while True:
            try:
                await self.check()
            except Exception as exc:
                logger.error(f"Failed to check remote health: {exc}")
            await asyncio.sleep(self.probe.interval)
