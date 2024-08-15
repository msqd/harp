from decimal import Decimal

from pydantic import Field

from harp.config import Configurable


class RemoteProbeSettings(Configurable):
    """
    A ``HttpProbe`` is a health check that can be used to check the health of a remote's endpoints. It is used as the
    configuration parser for ``proxy.endpoints[].remote.probe`` settings.

    .. code-block:: yaml

        type: http
        method: GET
        path: /health
        headers:
          x-purpose: "health probe"
        timeout: 5.0
    """

    method: str = "GET"
    path: str = "/"
    headers: dict = Field(default_factory=dict)
    interval: Decimal = 10.0
    timeout: Decimal = 10.0
    verify: bool = True
