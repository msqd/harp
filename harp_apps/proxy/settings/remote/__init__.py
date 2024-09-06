import asyncio
import warnings
from collections import deque
from typing import Iterable, List, Mapping, Optional

from _operator import attrgetter
from pydantic import Field, computed_field, field_serializer, field_validator, model_validator

from harp import get_logger
from harp.config import Configurable, Stateful
from harp.utils.background import is_event_loop_running
from harp.utils.urls import normalize_url
from harp_apps.proxy.constants import (
    ALL_BREAK_ON_VALUES,
    BREAK_ON_NETWORK_ERROR,
    BREAK_ON_UNHANDLED_EXCEPTION,
    CHECKING,
    DEFAULT_POOL,
    DOWN,
    FALLBACK_POOL,
    UP,
)

from ..liveness import InheritLivenessSettings, Liveness, LivenessSettings, NaiveLiveness, NaiveLivenessSettings
from .endpoint import RemoteEndpoint, RemoteEndpointSettings
from .probe import RemoteProbe, RemoteProbeSettings

logger = get_logger(__name__)

__all__ = [
    "Remote",
    "RemoteEndpoint",
    "RemoteEndpointSettings",
    "RemoteProbe",
    "RemoteProbeSettings",
    "RemoteSettings",
]


DEFAULT_LIVENESS = NaiveLiveness(settings=NaiveLivenessSettings())


class BaseRemoteSettings(Configurable):
    #: Minimum number of active endpoints to (try to) keep in the pool.
    min_pool_size: int = 1

    #: Events triggering the circuit breaker.
    break_on: list[str] = [BREAK_ON_NETWORK_ERROR, BREAK_ON_UNHANDLED_EXCEPTION]

    #: Delay after which endpoints that are marked as down will be checked again.
    check_after: float = 10.0

    @field_validator("break_on")
    @classmethod
    def __validate_break_on(cls, value: list) -> list:
        value = set(value)
        if not value.issubset(ALL_BREAK_ON_VALUES):
            raise ValueError(f"Invalid break_on values: {value}")
        return list(value)

    @field_serializer("break_on", when_used="json")
    @classmethod
    def __serialize_break_on(cls, value: Iterable[str]):
        return list(sorted(value))


class RemoteSettings(BaseRemoteSettings):
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

    endpoints: list[RemoteEndpointSettings] = None
    probe: Optional[RemoteProbeSettings] = None
    liveness: LivenessSettings = InheritLivenessSettings()

    def __getitem__(self, item):
        item = normalize_url(item)
        for endpoint in self.endpoints:
            if str(endpoint.url) == item:
                return endpoint
        raise KeyError(f'Endpoint "{item}" not found.')


class Remote(Stateful[RemoteSettings]):
    #: Current pool deque contains the list of available URLs, from least recently used to most recently used. It will
    #: be rotated on each request to implement a naive round-robin strategy.
    _current_pool: deque[RemoteEndpoint] = None

    #: Name of the currently used pool. This does not mean that all urls come from this pool, as the fallback pool may
    #: be active although some urls from default pool are still available.
    current_pool_name: str = DEFAULT_POOL

    #: Remote endpoints with current status.
    _endpoints: Mapping[str, RemoteEndpoint] = None

    #: Probe reference
    probe: Optional[RemoteProbe] = None

    #: Liveness
    liveness: Liveness = Field(None, exclude=True)

    @computed_field
    @property
    def current_pool(self) -> List[str]:
        return list(map(attrgetter("settings.url"), self._current_pool))

    @computed_field
    @property
    def endpoints(self) -> List[RemoteEndpoint]:
        return list(self._endpoints.values())

    @model_validator(mode="after")
    def __initialize(self):
        self._endpoints = {
            normalize_url(str(endpoint_settings.url)): RemoteEndpoint(settings=endpoint_settings)
            for endpoint_settings in (self.settings.endpoints or ())
        }
        self._current_pool = deque()
        self.probe = RemoteProbe(settings=self.settings.probe) if self.settings.probe else None

        # build our liveness object, or use default if it is set to inherit
        if self.settings.liveness.type == "inherit":
            self.liveness = DEFAULT_LIVENESS
        else:
            # If it quacks, it's a duck.
            try:
                self.liveness = self.settings.liveness.build_impl()
            except AttributeError as exc:
                raise NotImplementedError(
                    f"Unsupported liveness type: {self.settings.liveness.type}. The underlying setting of type "
                    f"{type(self.settings.liveness).__name__} must implement a build_impl method."
                ) from exc

        # replace the endpoint liveness object by ours if it is set to inherit
        for url, endpoint in self._endpoints.items():
            if endpoint.liveness.settings.type == "inherit":
                endpoint.liveness = self.liveness

        # set the initial pool of available remote endpoints
        self.refresh()

    def __getitem__(self, url: str) -> RemoteEndpoint:
        return self._endpoints[normalize_url(url)]

    def refresh(self):
        """Recompute the current pool of endpoints."""
        refreshed: deque[RemoteEndpoint] = deque()
        for endpoint in self._endpoints.values():
            if DEFAULT_POOL in endpoint.settings.pools and endpoint.status >= CHECKING:
                refreshed.append(endpoint)

        if len(refreshed) < self.settings.min_pool_size:
            for endpoint in self._endpoints.values():
                if FALLBACK_POOL in endpoint.settings.pools and endpoint.status >= CHECKING:
                    self.current_pool_name = FALLBACK_POOL
                    refreshed.append(endpoint)
        else:
            self.current_pool_name = DEFAULT_POOL

        self._current_pool = refreshed

    def get_url(self) -> str:
        """Get next candidate url from the current pool, then rotate."""
        try:
            return str(self._current_pool[0].settings.url)
        except IndexError as exc:
            raise IndexError("No available URLs for remote.") from exc

        finally:
            self._current_pool.rotate(-1)

    def notify_url_status(self, url, status):
        """
        Take into account a http status code to update the status of the url. Behaviour differs depending on the
        instance configuration (some considers 5xx as down, some ignores non-network errors).
        """
        if ("http_5xx" in self.settings.break_on and 500 <= status < 600) or (
            "http_4xx" in self.settings.break_on and 400 <= status < 500
        ):
            if self[url].failure(f"HTTP_{status}"):
                self.refresh()

    def set_down(self, url):
        old_status = self[url].status

        self[url].status = DOWN

        if old_status >= DOWN:
            if is_event_loop_running():

                async def delayed_set_checking():
                    await asyncio.sleep(self.settings.check_after)
                    if self[url].status == DOWN:
                        self.set_checking(url)
                    del self[url]._delayed_set_checking

                try:
                    self[url]._delayed_set_checking = asyncio.create_task(delayed_set_checking())
                except RuntimeError as exc:
                    warnings.warn(f"Failed to schedule delayed checking state: {exc}")

        self.refresh()

    def set_checking(self, url):
        self[url].status = CHECKING
        self.refresh()

    def set_up(self, url):
        self[url].status = UP
        self.refresh()

    async def check(self):
        """Uses the probe (luke), to check the health of each urls. It is also done on fallback and inactive urls, to
        ensure that they are ready in case we need them."""
        if self.probe is None:
            return

        state_changed = False

        async with self.probe.async_client() as client:
            for endpoint in self._endpoints.values():
                url_state_changed = await self.probe.check(client, endpoint)
                state_changed |= url_state_changed

        if state_changed:
            self.refresh()

    async def check_forever(self):
        while True:
            try:
                await self.check()
            except Exception as exc:
                logger.error(f"Failed to check remote health: {exc}")
            await asyncio.sleep(self.probe.settings.interval)
