from typing import Optional

from harp.config import StatefulConfigurableWrapper
from harp_apps.proxy.constants import CHECKING, DOWN, UP
from harp_apps.proxy.settings.remote import RemoteEndpointSettings


class RemoteEndpoint(StatefulConfigurableWrapper[RemoteEndpointSettings]):
    status: int
    failure_score: int
    success_score: int
    failure_reasons: Optional[set] = None

    def __init__(self, settings: RemoteEndpointSettings):
        super().__init__(settings)

        self.status = CHECKING
        self.failure_score = 0
        self.success_score = 0

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


"""
    status: int = CHECKING

    def __post_init__(self):
        self.url = normalize_url(self.url)
        self.pools = set(self.pools)
        unknown_pools = self.pools.difference({DEFAULT_POOL, FALLBACK_POOL})
        if len(unknown_pools):
            raise ValueError(f"Invalid pool names: {unknown_pools}")


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
"""
