from hishel import HEURISTICALLY_CACHEABLE_STATUS_CODES, AsyncCacheTransport, Controller
from httpx import AsyncClient, AsyncHTTPTransport

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent
from harp.settings import DEFAULT_TIMEOUT

from .settings import HttpClientSettings

logger = get_logger(__name__)


class AsyncHttpClient(AsyncClient):
    settings: HttpClientSettings

    def __init__(self, settings: HttpClientSettings):
        transport = AsyncHTTPTransport()
        if not (settings.cache and settings.cache.disabled):
            controller = Controller(
                allow_heuristics=True,
                cacheable_methods=settings.cache.cacheable_methods if settings.cache else None,
                cacheable_status_codes=(
                    settings.cache.cacheable_status_codes
                    if settings.cache
                    else list(HEURISTICALLY_CACHEABLE_STATUS_CODES)
                ),
                allow_stale=True,
            )
            transport = AsyncCacheTransport(transport=transport, controller=controller)

        super().__init__(transport=transport, timeout=settings.timeout)


class HttpClientApplication(Application):
    settings_namespace = "http_client"
    settings_type = HttpClientSettings

    @classmethod
    def defaults(cls, settings=None) -> dict:
        settings = settings if settings is not None else {}
        settings.setdefault("timeout", DEFAULT_TIMEOUT)
        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(AsyncClient, AsyncHttpClient)
