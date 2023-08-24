from dataclasses import dataclass

from harp.models.proxy_endpoint import ProxyEndpoint, ProxyEndpointTarget


class ContentAddressable:
    def __init__(self, content: bytes):
        self._hash = None

    def hash(self):
        if getattr(self, "_hash", None) is None:
            from hashlib import sha256

            self._hash = sha256(self.normalize()).hexdigest()

        return self._hash

    def normalize(self):
        raise NotImplementedError


@dataclass
class Request(ContentAddressable):
    method: str
    url: str
    headers: tuple
    body: bytes | None
    endpoint: ProxyEndpoint | None = None

    def asdict(self):
        return {
            "id": self.hash(),
            "method": self.method,
            "url": self.endpoint.contextualize(self.url) if self.endpoint else self.url,
        }

    def normalize(self):
        return b"\n".join(
            (
                f"HTTP {self.method} {self.url}".encode(),
                b"",
                *(k + b": " + v for k, v in self.headers),
                b"",
                self.body or b"",
            )
        )

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
class Response(ContentAddressable):
    status_code: int
    headers: tuple
    body: bytes

    def asdict(self):
        return {
            "id": self.hash(),
            "statusCode": self.status_code,
        }

    def normalize(self):
        return b"\n".join(
            (
                f"HTTP {self.status_code}".encode(),
                b"",
                *(k + b": " + v for k, v in self.headers),
                b"",
                self.body or b"",
            )
        )
