from functools import cached_property

from harp.config import Configurable, Stateful

from .endpoint import Endpoint, EndpointSettings
from .remote import Remote, RemoteEndpoint, RemoteEndpointSettings, RemoteProbe, RemoteProbeSettings, RemoteSettings

__all__ = [
    "Endpoint",
    "EndpointSettings",
    "Proxy",
    "ProxySettings",
    "Remote",
    "RemoteEndpoint",
    "RemoteEndpointSettings",
    "RemoteProbe",
    "RemoteProbeSettings",
    "RemoteSettings",
]


class BaseProxySettings(Configurable):
    pass


class ProxySettings(BaseProxySettings):
    """
    Configuration parser for ``proxy`` settings.

    .. code-block:: yaml

        endpoints:
          # see ProxyEndpoint
          - ...

    """

    endpoints: list[EndpointSettings] = []


class Proxy(Stateful[ProxySettings]):
    @cached_property
    def endpoints(self) -> list[Endpoint]:
        return [Endpoint(settings=settings) for settings in self.settings.endpoints]
