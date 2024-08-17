from harp.config import Configurable, Stateful

from .endpoint import EndpointSettings
from .remote import Remote, RemoteEndpoint, RemoteEndpointSettings, RemoteProbe, RemoteProbeSettings, RemoteSettings

__all__ = [
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
    pass
