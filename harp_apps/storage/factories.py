from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from harp.utils.services import factory
from harp_apps.storage.settings import StorageSettings


@factory(AsyncEngine)
def AsyncEngineFactory(self, settings: StorageSettings) -> AsyncEngine:
    return create_async_engine(settings.url)
