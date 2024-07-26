from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

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


class Remote:
    name = None
    url_statuses = None
    current_pool = None
    mode = None

    def __init__(self, name, /, *, base_urls: Iterable = (), fallback_urls: Iterable = (), min_pool_size=1):
        self.name = name
        self.mode = DEFAULT_POOL

        self.url_statuses = {}
        for url in base_urls:
            url = normalize_url(url)
            self.url_statuses.setdefault(url, Url(url=url))
            self.url_statuses[url].pools.add(DEFAULT_POOL)

        for url in fallback_urls:
            url = normalize_url(url)
            self.url_statuses.setdefault(url, Url(url=url))
            self.url_statuses[url].pools.add(FALLBACK_POOL)

        self.min_pool_size = max(0, min_pool_size)
        self.current_pool = deque()
        self.refresh()

    def refresh(self):
        refreshed = deque()
        for url in self.url_statuses.values():
            if DEFAULT_POOL in url.pools and url.status >= CHECKING:
                refreshed.append(url)

        if len(refreshed) < self.min_pool_size:
            for url in self.url_statuses.values():
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
        url = self.url_statuses[url]
        url.status = DOWN
        self.refresh()

    def set_up(self, url):
        url = normalize_url(url)
        url = self.url_statuses[url]
        url.status = UP
        self.refresh()
