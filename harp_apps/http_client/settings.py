from dataclasses import field
from typing import List, Optional

from hishel import HEURISTICALLY_CACHEABLE_STATUS_CODES

from harp.config.settings.base import BaseSetting, settings_dataclass
from harp.settings import DEFAULT_TIMEOUT


def default_status_codes() -> List[int]:
    return list(HEURISTICALLY_CACHEABLE_STATUS_CODES)


@settings_dataclass
class ControllerSettings:
    allow_heuristics: bool = True
    allow_stale: bool = True
    cacheable_methods: Optional[List[str]] = field(default_factory=lambda: ["GET"])
    cacheable_status_codes: List[int] = field(default_factory=default_status_codes)


@settings_dataclass
class CacheSettings:
    enabled: Optional[bool] = True
    controller: ControllerSettings = field(default_factory=ControllerSettings)

    def __post_init__(self):
        if self.controller:
            self.controller = (
                self.controller
                if isinstance(self.controller, ControllerSettings)
                else ControllerSettings(**self.controller)
            )


@settings_dataclass
class HttpClientSettings(BaseSetting):
    timeout: Optional[float] = DEFAULT_TIMEOUT
    cache: CacheSettings = field(default_factory=CacheSettings)

    def __post_init__(self):
        if self.cache:
            self.cache = self.cache if isinstance(self.cache, CacheSettings) else CacheSettings(**self.cache)
