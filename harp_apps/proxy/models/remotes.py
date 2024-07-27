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
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
        }


class HttpProbe:
    def __init__(
        self,
        method: str,
        path: str,
        headers=None,
        timeout=10,
    ):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.timeout = timeout

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
            "timeout": self.timeout,
        }


class HttpRemote:
    name = None
    endpoints = None
    current_pool = None
    current_pool_name = None

    def __init__(
        self,
        urls: Iterable = (),
        fallback_urls: Iterable = (),
        min_pool_size=1,
        probe: HttpProbe = None,
    ):
        self.current_pool_name = DEFAULT_POOL

        if isinstance(probe, dict):
            probe = HttpProbe(**probe)
        self.probe = probe

        self.endpoints = {}
        for _url in urls:
            endpoint = HttpEndpoint(url=_url)
            self.endpoints.setdefault(endpoint.url, endpoint)
            self.endpoints[endpoint.url].pools.add(DEFAULT_POOL)

        for _url in fallback_urls:
            endpoint = HttpEndpoint(url=_url)
            self.endpoints.setdefault(endpoint.url, endpoint)
            self.endpoints[endpoint.url].pools.add(FALLBACK_POOL)

        self.min_pool_size = max(0, min_pool_size)
        self.current_pool = deque()
        self.refresh()

    def __getitem__(self, url):
        return self.endpoints[normalize_url(url)]

    def refresh(self):
        refreshed = deque()
        for url in self.endpoints.values():
            if DEFAULT_POOL in url.pools and url.status >= CHECKING:
                refreshed.append(url)

        if len(refreshed) < self.min_pool_size:
            for url in self.endpoints.values():
                if FALLBACK_POOL in url.pools and url.status >= CHECKING:
                    self.current_pool_name = FALLBACK_POOL
                    refreshed.append(url)
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
            "min_pool_size": self.min_pool_size,
            **({"probe": self.probe._asdict(secure=secure)} if self.probe else {}),
        }
