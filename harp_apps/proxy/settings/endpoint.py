from typing import Optional

from pydantic import Field, model_validator

from harp.config import Configurable, LazyService, Service, Stateful
from harp_apps.proxy.settings.remote import Remote, RemoteEndpointSettings, RemoteSettings


class BaseEndpointSettings(Configurable):
    #: endpoint name, used as an unique identifier
    name: str

    #: port to listen on
    port: Optional[int] = None

    #: description, informative only
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
        controller : optional controller Service definition, default to HttpProxyController

    A shorthand syntax is also available for cases where you only need to proxy to a single URL and do not require
    fine-tuning the endpoint settings:

    .. code-block:: yaml

        name: my-endpoint
        port: 8080
        description: My endpoint
        url: http://my-endpoint:8080

    """

    #: remote definition, with url pools, probes, etc.
    remote: Optional[RemoteSettings] = Field(None, repr=False)

    #: custom controller
    controller: Optional[Service | str] = Service(
        type="harp_apps.proxy.controllers.HttpProxyController",
        arguments={"dispatcher": LazyService(type="IAsyncEventDispatcher")},
    )

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
        if "controller" in values and isinstance(values["controller"], str):
            values["controller"] = Service(type=values["controller"])

        return values


class Endpoint(Stateful[EndpointSettings]):
    remote: Remote = None

    @model_validator(mode="after")
    def __initialize(self):
        self.remote = Remote(settings=self.settings.remote) if self.settings.remote else None
        return self
