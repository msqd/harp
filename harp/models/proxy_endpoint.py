from dataclasses import dataclass
from functools import cached_property
from urllib.parse import urljoin


class ProxyEndpoint:
    def __init__(self, url, *, name=None):
        self.name = name
        self.url = url

    def get_target(self, scope):
        return ProxyEndpointTarget.from_scope(self, scope)

    def contextualize(self, url):
        if url.startswith(self.url):
            return urljoin("/", url[len(self.url) :])
        return url


@dataclass(frozen=True)
class ProxyEndpointTarget:
    # info about the endpoint used
    endpoint: ProxyEndpoint

    # info about the request
    method: str
    path: str
    query_string: str
    headers: tuple = ()

    @classmethod
    def from_scope(cls, endpoint: ProxyEndpoint, scope):
        return cls(
            endpoint=endpoint,
            method=scope["method"],
            path=scope["raw_path"].decode("utf-8"),
            query_string=scope["query_string"].decode("utf-8"),
            headers=tuple(((k, v) for k, v in scope["headers"] if k.lower() not in (b"host",))),
        )

    @cached_property
    def url(self):
        return self.endpoint.url

    @cached_property
    def full_url(self):
        return urljoin(self.url, self.path) + (f"?{self.query_string}" if self.query_string else "")
