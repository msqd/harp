from typing import Optional

from pydantic import Field, model_validator

from harp.config import Configurable, Stateful
from harp_apps.proxy.settings.remote import Remote, RemoteEndpointSettings, RemoteSettings


class BaseEndpointSettings(Configurable):
    name: str
    port: int
    description: Optional[str] = None


class EndpointSettings(BaseEndpointSettings):
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

    # resilience-compatible remote definition, with url pools, probes, etc.
    remote: Optional[RemoteSettings] = Field(None, repr=False)

    @model_validator(mode="before")
    @classmethod
    def __prepare(cls, values):
        # Convert old school urls into new style remotes
        if "url" in values and values["url"] is not None:
            if "remote" in values and values["remote"] is not None:
                raise ValueError(
                    "You can't define both proxy.endpoints[].remote and proxy.endpoints[].url, the second one is just "
                    "a historical shorthand syntax for the first one."
                )
            values["remote"] = RemoteSettings(endpoints=[RemoteEndpointSettings(url=values.pop("url"))])
        return values


class Endpoint(Stateful[EndpointSettings]):
    remote: Remote = None

    @model_validator(mode="after")
    def __initialize(self):
        self.remote = Remote(settings=self.settings.remote) if self.settings.remote else None
