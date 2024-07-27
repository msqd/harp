from dataclasses import field
from typing import TYPE_CHECKING, Optional

from hishel import HEURISTICALLY_CACHEABLE_STATUS_CODES

if TYPE_CHECKING:
    from hishel import AsyncCacheTransport, Controller
    from hishel._async._storages import AsyncBaseStorage
    from httpx import AsyncHTTPTransport

from harp.config import Definition, DisableableBaseSettings, Lazy, Settings, settings_dataclass
from harp.settings import DEFAULT_TIMEOUT


@settings_dataclass
class CacheSettings(DisableableBaseSettings):
    transport: Definition["AsyncCacheTransport"] = Lazy("hishel:AsyncCacheTransport")
    controller: Definition["Controller"] = Lazy(
        "hishel:Controller",
        allow_heuristics=False,
        allow_stale=False,
        cacheable_methods=["GET", "HEAD"],
        cacheable_status_codes=list(HEURISTICALLY_CACHEABLE_STATUS_CODES),
    )
    storage: Definition["AsyncBaseStorage"] = Lazy(None)
    ttl: Optional[float] = None
    check_ttl_every: float = 60


@settings_dataclass
class HttpClientSettings(Settings):
    timeout: Optional[float] = DEFAULT_TIMEOUT
    cache: CacheSettings = field(default_factory=CacheSettings)

    #: HTTP transport to use for the client. This is usually a httpx.AsyncHTTPTransport (or subclass) instance.
    transport: Definition["AsyncHTTPTransport"] = Lazy("httpx:AsyncHTTPTransport")

    def __post_init__(self):
        super().__post_init__()

        if self.cache and isinstance(self.cache, dict):
            self.cache = CacheSettings(**self.cache)
