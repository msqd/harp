from typing import List, Optional

from pydantic import Field, HttpUrl, field_serializer, field_validator, model_validator

from harp.config import Configurable, Stateful
from harp_apps.proxy.constants import AVAILABLE_POOLS, CHECKING
from harp_apps.proxy.settings.liveness import InheritLiveness, InheritLivenessSettings, Liveness, LivenessSettings


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
    liveness: LivenessSettings = Field(default_factory=InheritLivenessSettings)

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
    failure_reasons: Optional[set] = None
    liveness: Liveness = Field(None, exclude=True)

    @model_validator(mode="after")
    def __initialize(self):
        if self.liveness is None and self.settings.liveness is not None:
            if self.settings.liveness.type == "inherit":
                self.liveness = InheritLiveness(settings=self.settings.liveness)
            else:
                # If it quacks, it's a duck.
                try:
                    self.liveness = self.settings.liveness.build_impl()
                except AttributeError as exc:
                    raise NotImplementedError(
                        f"Unsupported liveness type: {self.settings.liveness.type}. The underlying setting of type "
                        f"{type(self.settings.liveness).__name__} must implement a build_impl method."
                    ) from exc

    def success(self) -> bool:
        """Returns a boolean indicating if a state change happened."""
        return self.liveness.success(self) if self.liveness else False

    def failure(self, reason: str = None):
        """Returns a boolean indicating if a state change happened."""
        return self.liveness.failure(self, reason) if self.liveness else False
