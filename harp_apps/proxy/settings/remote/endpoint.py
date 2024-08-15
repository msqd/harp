from typing import Annotated, FrozenSet, Set

from pydantic import Field, HttpUrl, field_serializer, field_validator

from harp.config import Configurable
from harp_apps.proxy.constants import AVAILABLE_POOLS


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
    pools: Set[str] = {"default"}
    failure_threshold: Annotated[int, Field(gt=0)] = 1
    success_threshold: Annotated[int, Field(gt=0)] = 1

    @field_validator("pools")
    @classmethod
    def validate_pools(cls, pools: FrozenSet[str]) -> FrozenSet[str]:
        if not pools.issubset(AVAILABLE_POOLS):
            raise ValueError(f"Invalid pool names: {', '.join(pools.difference(AVAILABLE_POOLS))}.")
        return pools

    @field_serializer("pools", when_used="json")
    @classmethod
    def serialize_in_order(cls, value: Set[str]):
        return sorted(value)
