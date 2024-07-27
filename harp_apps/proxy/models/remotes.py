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
class Url:
    url: str
    status: int = CHECKING
    pools: set = field(default_factory=set)
    failure_threshold: int = 3
    success_threshold: int = 1

    failure_score = 0
    success_score = 0
    failure_reasons = None

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


class Probe:
    def __init__(
        self,
        method: str,
        path: str,
        *,
        headers=None,
        timeout=10,
        initial_delay=0,
        period=30,
    ):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.timeout = timeout

        # not the right place
        self.initial_delay = initial_delay
        self.period = period

    def check(self, client: httpx.Client, url: Url):
        try:
            response = client.request(
                self.method, urljoin(url.url, self.path), headers=copy(self.headers), timeout=self.timeout
            )
            if 200 <= response.status_code < 400:
                url.probe_success()
            else:
                url.probe_failure(f"HTTP_{response.status_code}")
        except Exception as exc:
            url.probe_failure(shouty_snake(type(exc).__name__))


class Remote:
    name = None
    urls = None
    current_pool = None
    mode = None

    def __init__(
        self,
        name,
        *,
        base_urls: Iterable = (),
        fallback_urls: Iterable = (),
        min_pool_size=1,
        probe: Probe = None,
    ):
        self.name = name
        self.mode = DEFAULT_POOL
        self.probe = probe

        self.urls = {}
        for url in base_urls:
            url = normalize_url(url)
            self.urls.setdefault(url, Url(url=url))
            self.urls[url].pools.add(DEFAULT_POOL)

        for url in fallback_urls:
            url = normalize_url(url)
            self.urls.setdefault(url, Url(url=url))
            self.urls[url].pools.add(FALLBACK_POOL)

        self.min_pool_size = max(0, min_pool_size)
        self.current_pool = deque()
        self.refresh()

    def refresh(self):
        refreshed = deque()
        for url in self.urls.values():
            if DEFAULT_POOL in url.pools and url.status >= CHECKING:
                refreshed.append(url)

        if len(refreshed) < self.min_pool_size:
            for url in self.urls.values():
                if FALLBACK_POOL in url.pools and url.status >= CHECKING:
                    self.mode = FALLBACK_POOL
                    refreshed.append(url)
        else:
            self.mode = DEFAULT_POOL

        self.current_pool = refreshed

    def get_url(self):
        try:
            return self.current_pool[0].url
        except IndexError as exc:
            raise IndexError(f"No available URLs for remote «{self.name}».") from exc

        finally:
            self.current_pool.rotate(-1)

    def set_down(self, url):
        url = normalize_url(url)
        url = self.urls[url]
        url.status = DOWN
        self.refresh()

    def set_up(self, url):
        url = normalize_url(url)
        url = self.urls[url]
        url.status = UP
        self.refresh()

    def check(self):
        """Uses the probe (luke), to check the health of each urls. It is also done on fallback and inactive urls, to
        ensure that they are ready in case we need them."""
        with httpx.Client() as client:
            for url in self.urls.values():
                self.probe.check(client, url)

    def __getitem__(self, url):
        return self.urls[normalize_url(url)]
