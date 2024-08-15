from functools import cached_property

from harp.config import StatefulConfigurableWrapper

from ..settings import EndpointSettings
from .remote import Remote, RemoteEndpoint, RemoteProbe


class Endpoint(StatefulConfigurableWrapper[EndpointSettings]):
    @cached_property
    def remote(self) -> Remote:
        return Remote(self.settings.remote)


__all__ = [
    "Endpoint",
    "Remote",
    "RemoteEndpoint",
    "RemoteProbe",
]
