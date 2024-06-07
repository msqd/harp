from dataclasses import field
from typing import TYPE_CHECKING, Optional

from hishel import HEURISTICALLY_CACHEABLE_STATUS_CODES

if TYPE_CHECKING:
    from hishel import AsyncCacheTransport, Controller
    from hishel._async._storages import AsyncBaseStorage
    from httpx import AsyncHTTPTransport

from harp.config import BaseSetting, Definition, DisableableBaseSettings, Lazy, settings_dataclass
from harp.settings import DEFAULT_TIMEOUT


@settings_dataclass
class CacheSettings(DisableableBaseSettings):
    transport: Definition["AsyncCacheTransport"] = Lazy("hishel:AsyncCacheTransport")
    controller: Definition["Controller"] = Lazy(
        "hishel:Controller",
        allow_heuristics=True,
        allow_stale=True,
        cacheable_methods=["GET", "HEAD"],
        cacheable_status_codes=list(HEURISTICALLY_CACHEABLE_STATUS_CODES),
    )
    storage: Definition["AsyncBaseStorage"] = Lazy(None)


@settings_dataclass
class HttpClientSettings(BaseSetting):
    timeout: Optional[float] = DEFAULT_TIMEOUT
    cache: CacheSettings = field(default_factory=CacheSettings)

    #: HTTP transport to use for the client. This is usually a httpx.AsyncHTTPTransport (or subclass) instance.
    transport: Definition["AsyncHTTPTransport"] = Lazy("httpx:AsyncHTTPTransport")

    def __post_init__(self):
        super().__post_init__()

        if self.cache and isinstance(self.cache, dict):
            self.cache = CacheSettings(**self.cache)
