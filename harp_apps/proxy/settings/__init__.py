from harp.config import Configurable

from .endpoint import EndpointSettings


class ProxySettings(Configurable):
    """
    Configuration parser for ``proxy`` settings.

    .. code-block:: yaml

        endpoints:
          # see ProxyEndpoint
          - ...

    """

    endpoints: list[EndpointSettings] = []
