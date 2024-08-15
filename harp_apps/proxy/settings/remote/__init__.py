from decimal import Decimal
from typing import Iterable, Optional

from pydantic import field_serializer, field_validator

from harp.config import Configurable
from harp.utils.urls import normalize_url
from harp_apps.proxy.constants import ALL_BREAK_ON_VALUES, BREAK_ON_NETWORK_ERROR, BREAK_ON_UNHANDLED_EXCEPTION
from harp_apps.proxy.settings.remote.probe import RemoteProbeSettings

from .endpoint import RemoteEndpointSettings


class RemoteSettings(Configurable):
    """
    A ``HttpRemote`` is a collection of endpoints that a proxy will use to route requests. It is used as the
    configuration parser for ``proxy.endpoints[].remote`` settings.

    .. code-block:: yaml

        min_pool_size: 1
        endpoints:
          # see HttpEndpoint
          - ...
        probe:
          # see HttpProbe
          ...

    """

    min_pool_size: int = 1
    endpoints: list[RemoteEndpointSettings] = None
    probe: Optional[RemoteProbeSettings] = None

    #: Events triggering the circuit breaker.
    break_on: set = {BREAK_ON_NETWORK_ERROR, BREAK_ON_UNHANDLED_EXCEPTION}

    #: Delay after which endpoints that are marked as down will be checked again.
    check_after: Decimal = 10.0

    def __getitem__(self, item):
        item = normalize_url(item)
        for endpoint in self.endpoints:
            if str(endpoint.url) == item:
                return endpoint
        raise KeyError(f'Endpoint "{item}" not found.')

    @field_validator("break_on")
    @classmethod
    def validate_break_on(cls, value: set) -> set:
        if not value.issubset(ALL_BREAK_ON_VALUES):
            raise ValueError(f"Invalid break_on values: {value}")
        return value

    @field_serializer("break_on", when_used="json")
    @classmethod
    def serialize_in_order(cls, value: Iterable[str]):
        return sorted(value)

    """
    XXX: This is a work in progress


    current_pool: Deque[RemoteEndpointSettings] | None = None
    current_pool_name = None
    def __init__(
        self,
        endpoints: Iterable[HttpEndpoint | dict | str] | str = (),
        *,
        min_pool_size=None,
        probe: Optional[HttpProbe | dict] = None,
        break_on: Optional[set] = None,
    ):
        # endpoints
        self.endpoints = {}
        self.current_pool_name = DEFAULT_POOL
        self.current_pool = deque()

        if isinstance(endpoints, str):
            endpoints = [endpoints]
        for endpoint in endpoints:
            if isinstance(endpoint, str):
                endpoint = {"url": endpoint}
            if not isinstance(endpoint, HttpEndpoint):
                endpoint = HttpEndpoint(**endpoint)
            self.endpoints.setdefault(endpoint.url, endpoint)
            if not self.endpoints[endpoint.url].pools:
                self.endpoints[endpoint.url].pools.add(DEFAULT_POOL)

        # min pool size
        self.min_pool_size = max(0, min_pool_size or self.min_pool_size)

        # probe
        if isinstance(probe, dict):
            probe = HttpProbe(**probe)
        self.probe = probe

        # break on
        break_on = set(break_on) if break_on is not None else self.break_on
        if not break_on.issubset(ALL_BREAK_ON_VALUES):
            raise ValueError(f"Invalid break_on values: {break_on}")
        self.break_on = break_on

        # compute first pool
        self.refresh()






    def _asdict(self, /, *, secure=True, with_status=False):
        return {
            "endpoints": [
                endpoint._asdict(secure=secure, with_status=with_status) for endpoint in self.endpoints.values()
            ],
            **({"min_pool_size": self.min_pool_size} if self.min_pool_size != type(self).min_pool_size else {}),
            **({"probe": self.probe._asdict(secure=secure)} if self.probe else {}),
            **({"current_pool": list(x.url for x in self.current_pool)} if with_status else {}),
            **({"break_on": list(sorted(self.break_on))} if self.break_on != type(self).break_on else {}),
        }

"""
