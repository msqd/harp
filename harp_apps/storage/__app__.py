"""Storage Application"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent
from harp_apps.storage.services.sql import SqlStorage

from .factories import AsyncEngineFactory
from .settings import StorageSettings
from .types import IBlobStorage, IStorage

logger = get_logger(__name__)


class StorageApplication(Application):
    settings_namespace = "storage"
    settings_type = StorageSettings

    storage: Optional[IStorage]

    def __init__(self, settings=None, /):
        super().__init__(settings)
        self.storage = None

    @classmethod
    def supports(cls, settings):
        return settings.get("type", None) == "sqlalchemy"

    @classmethod
    def defaults(cls, settings=None):
        settings = settings if settings is not None else {"type": "sqlalchemy"}

        if cls.supports({"type": "sqlalchemy"} | settings):
            settings.setdefault("type", "sqlalchemy")
            settings.setdefault("url", "sqlite+aiosqlite:///:memory:")
            settings.setdefault("migrate", True)
            settings.setdefault("blobs", {"type": "sql"})
            settings["blobs"].setdefault("type", "sql")

        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(IStorage, SqlStorage)
        event.container.add_singleton(AsyncEngine, AsyncEngineFactory)

        blob_storage_type = self.settings.blobs.type
        if blob_storage_type == "sql":
            from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage

            event.container.add_singleton(IBlobStorage, SqlBlobStorage)
        elif blob_storage_type == "redis":
            from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage

            event.container.add_singleton(IBlobStorage, RedisBlobStorage)
        else:
            raise ValueError(f"Unsupported blob storage type: {blob_storage_type}")

    async def on_bound(self, event: FactoryBoundEvent):
        event.provider.get(IBlobStorage)

        self.storage = event.provider.get(IStorage)
        await self.storage.initialize()

    async def on_dispose(self, event: FactoryDisposeEvent):
        await self.storage.finalize()
