from dataclasses import field
from typing import Optional

from harp.config import Settings, asdict, settings_dataclass
from harp_apps.proxy.models.remotes import HttpRemote


@settings_dataclass
class ProxyEndpoint(Settings):
    name: str
    port: int
    description: Optional[str] = None

    # for backward compatibility, "short syntax"
    url: str = None

    # resilience-compatible remote definition, with url pools, probes, etc.
    remote: HttpRemote = None

    def __post_init__(self):
        if self.remote is not None and self.url is not None:
            raise ValueError(
                "You can't define both proxy.endpoints[].remote and proxy.endpoints[].url, the second one is just a "
                "shorthand syntax for the first one."
            )

        if self.url is not None:
            self.remote = HttpRemote([self.url])

        if isinstance(self.remote, dict):
            self.remote = HttpRemote(**self.remote)

        if not isinstance(self.remote, HttpRemote):
            raise ValueError(f"Invalid remote configuration: {self.remote}")

    def _asdict(self, /, *, secure=True):
        return {
            "name": self.name,
            "port": self.port,
            "description": self.description,
            "remote": asdict(self.remote, secure=secure),
        }


@settings_dataclass
class ProxySettings(Settings):
    endpoints: Optional[list[ProxyEndpoint]] = field(default_factory=list)

    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []

        self.endpoints = [
            endpoint if isinstance(endpoint, ProxyEndpoint) else ProxyEndpoint(**endpoint)
            for endpoint in self.endpoints
        ]
