from httpx import AsyncClient

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent

from .client import AsyncHttpClient
from .settings import HttpClientSettings

logger = get_logger(__name__)


class HttpClientApplication(Application):
    settings_namespace = "http_client"
    settings_type = HttpClientSettings

    @classmethod
    def defaults(cls, settings=None) -> dict:
        settings = settings if settings is not None else {}
        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(AsyncClient, AsyncHttpClient)
