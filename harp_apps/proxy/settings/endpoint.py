from typing import Optional

from pydantic import model_validator

from harp.config import Configurable
from harp_apps.proxy.settings.remote import RemoteEndpointSettings, RemoteSettings


class EndpointSettings(Configurable):
    """
    Configuration parser for ``proxy.endpoints[]`` settings.

    .. code-block:: yaml

        name: my-endpoint
        port: 8080
        description: My endpoint
        remote:
          # see HttpRemote
          ...

    A shorthand syntax is also available for cases where you only need to proxy to a single URL and do not require
    fine-tuning the endpoint settings:

    .. code-block:: yaml

        name: my-endpoint
        port: 8080
        description: My endpoint
        url: http://my-endpoint:8080

    """

    name: str
    port: int
    description: Optional[str] = None

    # for backward compatibility, "short syntax"
    url: Optional[str] = None

    # resilience-compatible remote definition, with url pools, probes, etc.
    remote: Optional[RemoteSettings] = None

    @model_validator(mode="before")
    @classmethod
    def convert_old_school_urls_to_remote(cls, values):
        if "url" in values and values["url"] is not None:
            if "remote" in values and values["remote"] is not None:
                raise ValueError(
                    "You can't define both proxy.endpoints[].remote and proxy.endpoints[].url, the second one is just "
                    "a historical shorthand syntax for the first one."
                )
            values["remote"] = RemoteSettings(endpoints=[RemoteEndpointSettings(url=values.pop("url"))])
        return values


"""
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

    def _asdict(self, /, *, secure=True, with_status=False):
        return {
            "name": self.name,
            "port": self.port,
            "description": self.description,
            "remote": self.remote._asdict(secure=secure, with_status=with_status),
        }
"""
