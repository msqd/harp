from typing import Optional

from harp.config.settings.base import BaseSetting, settings_dataclass
from harp.settings import DEFAULT_TIMEOUT


@settings_dataclass
class CacheSettings:
    cacheable_methods: Optional[list[str]] = None
    cacheable_status_codes: Optional[list[int]] = None
    disabled: Optional[bool] = False


@settings_dataclass
class HttpClientSettings(BaseSetting):
    cache: Optional[CacheSettings] = None
    timeout: Optional[float] = DEFAULT_TIMEOUT

    def __post_init__(self):
        if self.cache:
            self.cache = self.cache if isinstance(self.cache, CacheSettings) else CacheSettings(**self.cache)
