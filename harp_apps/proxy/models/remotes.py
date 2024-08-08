import asyncio
import warnings
from collections import deque
from copy import copy
from dataclasses import dataclass, field
from typing import Deque, Iterable, Optional
from urllib.parse import urljoin

import httpx
from pyheck import shouty_snake

from harp import get_logger
from harp.utils.urls import normalize_url

logger = get_logger(__name__)

DOWN = -1
CHECKING = 0
UP = 1

DEFAULT_POOL = "default"
FALLBACK_POOL = "fallback"


def humanize_status(status):
    return {CHECKING: "checking", UP: "up", DOWN: "down"}.get(status, "unknown")


@dataclass
class HttpEndpoint:
    """
    A ``HttpEndpoint`` is an instrumented target URL that a proxy will use to route requests. It is used as the
    configuration parser for ``proxy.endpoints[].remote.endpoints[]`` settings.

    .. code-block:: yaml

        url: "http://my-endpoint:8080"
        failure_threshold: 3
        success_threshold: 1
        pools: [fallback]  # omit for default pool
    """

    url: str
    status: int = CHECKING
    # todo is this the right place ? we don't use pools here but we need to define it in config. Maybe the pool logic
    #  should stay in HttpRemote
    pools: set = field(default_factory=set)
    failure_threshold: int = 1
    success_threshold: int = 1

    failure_score = 0
    success_score = 0
    failure_reasons = None

    def __post_init__(self):
        self.url = normalize_url(self.url)
        self.pools = set(self.pools)
        unknown_pools = self.pools.difference({DEFAULT_POOL, FALLBACK_POOL})
        if len(unknown_pools):
            raise ValueError(f"Invalid pool names: {unknown_pools}")

    def success(self):
        """Returns a boolean indicating if a state change happened."""
        self.failure_score = 0
        self.success_score += 1

        if self.success_score >= self.success_threshold:
            if self.status != UP:
                self.failure_reasons = None
                self.status = UP
                return True
        else:
            if self.status != CHECKING:
                self.status = CHECKING
                return True

        return False

    def failure(self, reason: str = None):
        """Returns a boolean indicating if a state change happened."""
        self.success_score = 0
        self.failure_score += 1

        if self.failure_reasons is None:
            self.failure_reasons = set()

        if reason:
            self.failure_reasons.add(reason)

        if self.failure_score >= self.failure_threshold:
            if self.status != DOWN:
                self.status = DOWN
                return True
        else:
            if self.status != CHECKING:
                self.status = CHECKING
                return True

        return False

    def _asdict(self, /, *, secure=True, with_status=False):
        return {
            "url": self.url,
            **(
                {"failure_threshold": self.failure_threshold}
                if self.failure_threshold != type(self).failure_threshold
                else {}
            ),
            **(
                {"success_threshold": self.success_threshold}
                if self.success_threshold != type(self).success_threshold
                else {}
            ),
            **({"pools": list(self.pools)} if len(self.pools) > 0 else {}),
            **({"status": humanize_status(self.status)} if with_status else {}),
            **({"failure_reasons": list(sorted(self.failure_reasons))} if with_status and self.failure_reasons else {}),
        }


class HttpProbe:
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

    interval = 10.0
    timeout = 10.0
    verify = True

    def __init__(
        self,
        method: str,
        path: str,
        verify=True,
        headers=None,
        timeout=None,
        type="http",
        interval=None,
    ):
        if type != "http":
            raise ValueError(f"Invalid probe type: {type}")

        self.method = method
        self.path = path
        self.headers = headers or {}
        self.timeout = float(timeout) if timeout else self.timeout
        self.interval = float(interval) if interval else self.interval
        self.verify = bool(verify)

    async def check(self, client: httpx.AsyncClient, url: HttpEndpoint):
        probe_url = urljoin(url.url, self.path)
        failure = None
        try:
            response = await client.request(
                self.method,
                probe_url,
                headers=copy(self.headers),
                timeout=self.timeout,
            )
            if 200 <= response.status_code < 400:
                return url.success()
            else:
                failure = f"HTTP_{response.status_code}"
                return url.failure(failure)
        except Exception as exc:
            failure = shouty_snake(type(exc).__name__)
            return url.failure(failure)
        finally:
            if failure:
                logger.info(f"Probe failure: {url.url} -> {failure}")

    def _asdict(self, /, *, secure=True):
        return {
            "type": "http",
            "method": self.method,
            "path": self.path,
            **({"headers": self.headers} if self.headers else {}),
            **({"timeout": self.timeout} if self.timeout != type(self).timeout else {}),
            **({"interval": self.interval} if self.interval != type(self).interval else {}),
            **({"verify": self.verify} if self.verify != type(self).verify else {}),
        }


ALL_BREAK_ON_VALUES = {"http_4xx", "http_5xx", "network_error"}


class HttpRemote:
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

    endpoints = None
    current_pool: Deque[HttpEndpoint] | None = None
    current_pool_name = None
    min_pool_size = 1
    probe: Optional[HttpProbe] = None

    #: Events triggering the circuit breaker.
    break_on = {"network_error"}

    #: Delay after which endpoints that are marked as down will be checked again.
    delay_for_checking_down_endpoints = 10.0

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

    def __getitem__(self, url) -> HttpEndpoint:
        return self.endpoints[normalize_url(url)]

    def refresh(self):
        refreshed: deque[HttpEndpoint] = deque()
        for endpoint in self.endpoints.values():
            if DEFAULT_POOL in endpoint.pools and endpoint.status >= CHECKING:
                refreshed.append(endpoint)

        if len(refreshed) < self.min_pool_size:
            for endpoint in self.endpoints.values():
                if FALLBACK_POOL in endpoint.pools and endpoint.status >= CHECKING:
                    self.current_pool_name = FALLBACK_POOL
                    refreshed.append(endpoint)
        else:
            self.current_pool_name = DEFAULT_POOL

        self.current_pool = refreshed

    def get_url(self):
        try:
            return self.current_pool[0].url
        except IndexError as exc:
            raise IndexError("No available URLs for remote.") from exc

        finally:
            self.current_pool.rotate(-1)

    def notify_url_status(self, url, status):
        """
        Take into account an http status code to update the status of the url. Behaviour differs depending on the
        instance configuration (some considers 5xx as down, some ignores non-network errors).
        """
        if ("http_5xx" in self.break_on and 500 <= status < 600) or (
            "http_4xx" in self.break_on and 400 <= status < 500
        ):
            if self[url].failure(f"HTTP_{status}"):
                self.refresh()

    def set_down(self, url):
        old_status = self[url].status

        self[url].status = DOWN

        if old_status >= DOWN:

            async def delayed_set_checking():
                await asyncio.sleep(self.delay_for_checking_down_endpoints)
                if self[url].status == DOWN:
                    self.set_checking(url)
                del self[url].delayed_set_checking

            try:
                self[url].delayed_set_checking = asyncio.create_task(delayed_set_checking())
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

        async with httpx.AsyncClient(verify=self.probe.verify) as client:
            for url in self.endpoints.values():
                url_state_changed = await self.probe.check(client, url)
                state_changed |= url_state_changed

        if state_changed:
            self.refresh()

    async def check_forever(self):
        while True:
            try:
                await self.check()
            except Exception as exc:
                logger.error(f"Failed to check remote health: {exc}")
            await asyncio.sleep(self.probe.interval)

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
