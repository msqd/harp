from hishel import AsyncCacheTransport, Controller
from httpx import AsyncClient, AsyncHTTPTransport

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent

from .settings import HttpClientSettings

logger = get_logger(__name__)


class AsyncHttpClient(AsyncClient):
    settings: HttpClientSettings

    def __init__(self, settings: HttpClientSettings):
        transport = AsyncHTTPTransport()
        if settings.cache.enabled:
            transport = AsyncCacheTransport(
                transport=transport,
                controller=Controller(
                    allow_heuristics=settings.cache.controller.allow_heuristics,
                    allow_stale=settings.cache.controller.allow_stale,
                    cacheable_methods=settings.cache.controller.cacheable_methods,
                    cacheable_status_codes=settings.cache.controller.cacheable_status_codes,
                ),
            )

        super().__init__(transport=transport, timeout=settings.timeout)


class HttpClientApplication(Application):
    settings_namespace = "http_client"
    settings_type = HttpClientSettings

    @classmethod
    def defaults(cls, settings=None) -> dict:
        settings = settings if settings is not None else {}
        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(AsyncClient, AsyncHttpClient)
