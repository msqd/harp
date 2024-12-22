from typing import TYPE_CHECKING

from pydantic import Field

from harp.config import Service
from harp_apps.http_client.settings.cache import CacheSettings

if TYPE_CHECKING:
    pass

from harp.settings import DEFAULT_TIMEOUT


class HttpClientSettings(Service):
    type: str = Field("httpx.AsyncClient", description=Service.model_fields["type"].description)
    arguments: dict = {"timeout": DEFAULT_TIMEOUT}

    cache: CacheSettings = CacheSettings()

    #: HTTP transport to use for the client. This is usually a httpx.AsyncHTTPTransport (or subclass) instance.
    transport: Service = Service(
        type="httpx.AsyncHTTPTransport",
        arguments={
            "verify": True,
            "retries": 0,
        },
    )

    proxy_transport: Service = Service(
        type="harp_apps.http_client.transport.AsyncFilterableTransport",
    )
