from dataclasses import dataclass

from harp.models.proxy_endpoint import ProxyEndpoint


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
