from typing import Annotated, List, Optional

from pydantic import Field, HttpUrl, field_serializer, field_validator

from harp.config import Configurable, Stateful
from harp_apps.proxy.constants import AVAILABLE_POOLS, CHECKING, DOWN, UP


class RemoteEndpointSettings(Configurable):
    """
    A ``HttpEndpoint`` is an instrumented target URL that a proxy will use to route requests. It is used as the
    configuration parser for ``proxy.endpoints[].remote.endpoints[]`` settings.

    .. code-block:: yaml

        url: "http://my-endpoint:8080"
        pools: [fallback]  # omit for default pool
        failure_threshold: 3
        success_threshold: 1
    """

    url: HttpUrl
    pools: List[str] = ["default"]
    failure_threshold: Annotated[int, Field(gt=0)] = 1
    success_threshold: Annotated[int, Field(gt=0)] = 1

    @field_validator("pools")
    @classmethod
    def validate_pools(cls, pools: List[str]) -> List[str]:
        pools = set(pools)
        if not pools.issubset(AVAILABLE_POOLS):
            raise ValueError(f"Invalid pool names: {', '.join(pools.difference(AVAILABLE_POOLS))}.")
        return list(pools)

    @field_serializer("pools", when_used="json")
    @classmethod
    def serialize_in_order(cls, value: List[str]):
        return list(sorted(value))


class RemoteEndpoint(Stateful[RemoteEndpointSettings]):
    """Stateful version of a remote endpoint definition."""

    status: int = CHECKING
    failure_score: int = 0
    success_score: int = 0
    failure_reasons: Optional[set] = None

    def success(self):
        """Returns a boolean indicating if a state change happened."""
        self.failure_score = 0
        self.success_score += 1

        if self.success_score >= self.settings.success_threshold:
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

        if self.failure_score >= self.settings.failure_threshold:
            if self.status != DOWN:
                self.status = DOWN
                return True
        else:
            if self.status != CHECKING:
                self.status = CHECKING
                return True

        return False
