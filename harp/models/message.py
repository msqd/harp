from dataclasses import dataclass

from harp.models.proxy_endpoint import ProxyEndpoint, ProxyEndpointTarget


@dataclass
class Request:
    method: str
    url: str
    headers: tuple
    body: bytes | None
    endpoint: ProxyEndpoint | None = None

    def asdict(self):
        return {
            "method": self.method,
            "url": self.endpoint.contextualize(self.url) if self.endpoint else self.url,
            "headers": self.headers,
            "body": self.body,
        }

    @classmethod
    def from_proxy_target(cls, target: ProxyEndpointTarget):
        return cls(
            method=target.method,
            url=target.full_url,
            headers=target.headers,
            body=None,
            endpoint=target.endpoint,
        )


@dataclass
class Response:
    status_code: int
    headers: tuple
    body: bytes

    def asdict(self):
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": self.body,
        }
