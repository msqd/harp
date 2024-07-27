from collections import deque
from copy import copy
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urljoin

import httpx
from pyheck import shouty_snake

from harp.utils.urls import normalize_url

CHECKING = 0
UP = 1
DOWN = -1

DEFAULT_POOL = "default"
FALLBACK_POOL = "fallback"


@dataclass
class HttpEndpoint:
    url: str
    status: int = CHECKING
    # todo is this the right place ? we don't use pools here but we need to define it in config. Maybe the pool logic
    #  should stay in HttpRemote
    pools: set = field(default_factory=set)
    failure_threshold: int = 3
    success_threshold: int = 1

    failure_score = 0
    success_score = 0
    failure_reasons = None

    def __post_init__(self):
        self.url = normalize_url(self.url)
        self.pools = set(self.pools)
        unknown_pools = self.pools.difference({DEFAULT_POOL, FALLBACK_POOL})
        if len(unknown_pools):
            raise ValueError(f"Invalid pool names: {unknown_pools}")

    def probe_success(self):
        self.failure_score = 0
        self.success_score += 1

        if self.success_score >= self.success_threshold:
            self.status = UP
        else:
            self.status = CHECKING

        self.failure_reasons = None

    def probe_failure(self, reason: str = None):
        self.success_score = 0
        self.failure_score += 1

        if self.failure_score >= self.failure_threshold:
            self.status = DOWN
        else:
            self.status = CHECKING

        if self.failure_reasons is None:
            self.failure_reasons = set()
        if reason:
            self.failure_reasons.add(reason)

    def _asdict(self, /, *, secure=True):
        return {
            "url": self.url,
            **(
                {"failure_threshold": self.failure_threshold}
                if self.failure_threshold != type(self).failure_threshold
                else {}
            ),
            **(
                {"success_threshold": self.success_threshold}
                if self.success_threshold != type(self).success_threshold
                else {}
            ),
        }


class HttpProbe:
    timeout = 10.0

    def __init__(
        self,
        method: str,
        path: str,
        headers=None,
        timeout=None,
    ):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.timeout = float(timeout) if timeout else self.timeout

    async def check(self, client: httpx.AsyncClient, url: HttpEndpoint):
        try:
            response = await client.request(
                self.method, urljoin(url.url, self.path), headers=copy(self.headers), timeout=self.timeout
            )
            if 200 <= response.status_code < 400:
                url.probe_success()
            else:
                url.probe_failure(f"HTTP_{response.status_code}")
        except Exception as exc:
            url.probe_failure(shouty_snake(type(exc).__name__))

    def _asdict(self, /, *, secure=True):
        return {
            "type": "http",
            "method": self.method,
            "path": self.path,
            **({"headers": self.headers} if self.headers else {}),
            **({"timeout": self.timeout} if self.timeout != type(self).timeout else {}),
        }


class HttpRemote:
    endpoints = None
    current_pool: deque[HttpEndpoint] = None
    current_pool_name = None

    min_pool_size = 1

    def __init__(
        self,
        endpoints: Iterable[HttpEndpoint | dict] | str = (),
        *,
        min_pool_size=None,
        probe: HttpProbe = None,
    ):
        self.current_pool_name = DEFAULT_POOL

        if isinstance(probe, dict):
            probe = HttpProbe(**probe)
        self.probe = probe

        self.endpoints = {}
        if isinstance(endpoints, str):
            endpoints = [endpoints]
        for endpoint in endpoints:
            if isinstance(endpoint, str):
                endpoint = {"url": endpoint}
            endpoint = HttpEndpoint(**endpoint)
            self.endpoints.setdefault(endpoint.url, endpoint)
            if not self.endpoints[endpoint.url].pools:
                self.endpoints[endpoint.url].pools.add(DEFAULT_POOL)

        self.min_pool_size = max(0, min_pool_size or self.min_pool_size)
        self.current_pool = deque()
        self.refresh()

    def __getitem__(self, url):
        return self.endpoints[normalize_url(url)]

    def refresh(self):
        refreshed: deque[HttpEndpoint] = deque()
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

    def get_url(self):
        try:
            return self.current_pool[0].url
        except IndexError as exc:
            raise IndexError("No available URLs for remote.") from exc

        finally:
            self.current_pool.rotate(-1)

    def set_down(self, url):
        self[url].status = DOWN
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
        async with httpx.AsyncClient() as client:
            for url in self.endpoints.values():
                await self.probe.check(client, url)

    def _asdict(self, /, *, secure=True):
        return {
            "endpoints": [endpoint._asdict(secure=secure) for endpoint in self.endpoints.values()],
            **({"min_pool_size": self.min_pool_size} if self.min_pool_size != type(self).min_pool_size else {}),
            **({"probe": self.probe._asdict(secure=secure)} if self.probe else {}),
        }
