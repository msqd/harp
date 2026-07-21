from pydantic import Field

from harp.config import ApplicationSettingsMixin, Service
from harp.settings import DEFAULT_TIMEOUT


class HttpClientSettings(ApplicationSettingsMixin, Service):
    type: str = Field("httpx.AsyncClient", description=Service.model_fields["type"].description)
    arguments: dict = {"timeout": DEFAULT_TIMEOUT}

    #: HTTP transport to use for the client. This is usually a httpx.AsyncHTTPTransport (or subclass) instance.
    transport: Service = Service(
        type="httpx.AsyncHTTPTransport",
        arguments={
            "verify": True,
            "retries": 0,
        },
    )

    proxy_transport: Service = Service(
        type="harp_apps.http_client.transports.AsyncFilterableTransport",
    )
