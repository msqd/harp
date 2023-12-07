from dataclasses import dataclass

from harp.models.proxy_endpoint import DeprecatedOldProxyEndpoint, DeprecatedOldProxyEndpointTarget

from .message import DeprecatedOldTransactionMessage


@dataclass(kw_only=True)
class DeprecatedOldTransactionRequest(DeprecatedOldTransactionMessage):
    method: str
    url: str

    endpoint: DeprecatedOldProxyEndpoint | None = None

    def normalize(self):
        return b"\n".join(
            (
                f"HTTP {self.method} {self.url}".encode(),
                b"",
                super().normalize(),
            )
        )

    def asdict(self, *, with_details=False):
        return super().asdict(with_details=with_details) | {
            "method": self.method,
            "url": self.endpoint.contextualize(self.url) if self.endpoint else self.url,
        }

    @classmethod
    def from_proxy_target(cls, target: DeprecatedOldProxyEndpointTarget):
        return cls(
            method=target.method,
            url=target.full_url,
            headers=target.headers,
            content=None,
            endpoint=target.endpoint,
        )
