from typing import Optional

from harp.core.settings import BaseSetting, settings_dataclass


@settings_dataclass
class ProxyEndpointSetting(BaseSetting):
    name: str
    port: int
    url: str

    description: Optional[str] = None


@settings_dataclass
class ProxySettings(BaseSetting):
    endpoints: Optional[list[ProxyEndpointSetting]]

    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []

        self.endpoints = [
            endpoint if isinstance(endpoint, ProxyEndpointSetting) else ProxyEndpointSetting(**endpoint)
            for endpoint in self.endpoints
        ]
