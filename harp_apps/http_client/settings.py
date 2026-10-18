from pydantic import Field

from harp.config import ApplicationSettingsMixin, Service
from harp.settings import DEFAULT_TIMEOUT


class HttpClientSettings(ApplicationSettingsMixin, Service):
    type: str = Field("httpx.AsyncClient", description=Service.model_fields["type"].description)
    arguments: dict = {"timeout": DEFAULT_TIMEOUT}

    #: HTTP transport to use for the client: any httpx transport. Set `httpx.AsyncHTTPTransport` for the pre-0.12 one.
    transport: Service = Service(
        type="harp_apps.http_client.aiohttp_transport.AiohttpTransport",
        arguments={
            "verify": True,
            "retries": 0,
        },
    )

    proxy_transport: Service = Service(
        type="harp_apps.http_client.transports.AsyncFilterableTransport",
    )
