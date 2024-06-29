"""
SqlAlchemy Storage Extension

"""

from typing import Callable, Optional, Type, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent
from harp_apps.sqlalchemy_storage.storages.sql import SqlStorage

from .settings import SqlAlchemyStorageSettings
from .types import IBlobStorage, IStorage

logger = get_logger(__name__)


T = TypeVar("T")


def factory(t: Type[T]) -> Callable[..., Type[T]]:
    def decorator(f) -> Type[T]:
        return cast(Type[T], type(f.__name__, (t,), {"__new__": f, "__init__": f}))

    return decorator


@factory(AsyncEngine)
def AsyncEngineFactory(self, settings: SqlAlchemyStorageSettings) -> AsyncEngine:
    return create_async_engine(settings.url)


class SqlalchemyStorageApplication(Application):
    settings_namespace = "storage"
    settings_type = SqlAlchemyStorageSettings

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
            from harp_apps.sqlalchemy_storage.storages.blobs.sql import SqlBlobStorage

            event.container.add_singleton(IBlobStorage, SqlBlobStorage)
        elif blob_storage_type == "redis":
            from harp_apps.sqlalchemy_storage.storages.blobs.redis import RedisBlobStorage

            event.container.add_singleton(IBlobStorage, RedisBlobStorage)
        else:
            raise ValueError(f"Unsupported blob storage type: {blob_storage_type}")

    async def on_bound(self, event: FactoryBoundEvent):
        event.provider.get(IBlobStorage)

        self.storage = event.provider.get(IStorage)
        await self.storage.initialize()

    async def on_dispose(self, event: FactoryDisposeEvent):
        await self.storage.finalize()
