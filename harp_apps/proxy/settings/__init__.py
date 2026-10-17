from functools import cached_property

from pydantic import ByteSize, Field

from harp.config import ApplicationSettingsMixin, Configurable, Stateful
from harp_apps.storage.constants import DEFAULT_MAX_RECORDED_BODY_SIZE

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


class ProxySettings(ApplicationSettingsMixin, BaseProxySettings):
    """
    Configuration parser for ``proxy`` settings.

    .. code-block:: yaml

        endpoints:
          # see ProxyEndpoint
          - ...

    """

    endpoints: list[EndpointSettings] = []

    #: How much of a request or response body is recorded, at most: a byte count or a size with its unit (``"1MiB"``). A
    #: longer body is still sent whole, recorded truncated and marked ``truncated-request-body`` or
    #: ``truncated-response-body``; a response is also not stored in the http cache.
    max_recorded_body_size: ByteSize = Field(ByteSize(DEFAULT_MAX_RECORDED_BODY_SIZE), gt=0)


class Proxy(Stateful[ProxySettings]):
    @cached_property
    def endpoints(self) -> list[Endpoint]:
        return [Endpoint(settings=settings) for settings in self.settings.endpoints]
