import pytest
from whistle import AsyncEventDispatcher

from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.storage import SqlAlchemyStorage


class SqlalchemyStorageTestFixtureMixin:
    storage_settings = {
        "url": "sqlite+aiosqlite:///:memory:",
        "echo": False,
    }

    async def create_storage(self, /, *, dispatcher=None, **settings) -> SqlAlchemyStorage:
        storage = SqlAlchemyStorage(
            dispatcher=dispatcher or AsyncEventDispatcher(),
            settings=SqlAlchemyStorageSettings(**self.storage_settings, **settings),
        )

        await storage.initialize()
        await storage.create_users(["anonymous"])
        return storage

    @pytest.fixture
    async def storage(self):
        yield await self.create_storage()
