from typing import cast

from httpx import AsyncClient

from harp import get_logger
from harp.config import FactoryBindEvent
from harp_apps.storage.services.blob_storages.null import NullBlobStorage
from harp_apps.storage.types import IBlobStorage

from .factories import AsyncClientFactory
from .settings import HttpClientSettings

logger = get_logger(__name__)


class HttpClientApplication:
    Settings = HttpClientSettings

    class Lifecycle:
        @staticmethod
        async def on_bind(event: FactoryBindEvent):
            if IBlobStorage not in event.container:
                event.container.add_singleton(IBlobStorage, NullBlobStorage)
            event.container.add_singleton(AsyncClient, cast(type(AsyncClient), AsyncClientFactory))
