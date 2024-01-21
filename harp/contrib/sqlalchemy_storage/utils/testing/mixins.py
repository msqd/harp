import pytest
from whistle import AsyncEventDispatcher

from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.storage import SqlAlchemyStorage


class SqlalchemyStorageFixtureMixin:
    echo = False

    @pytest.fixture
    async def storage(self):
        storage = SqlAlchemyStorage(
            dispatcher=AsyncEventDispatcher(),
            settings=SqlAlchemyStorageSettings(
                url="sqlite+aiosqlite:///:memory:",
                echo=self.echo,
            ),
        )
        await storage.initialize(force_reset=True)
        yield storage
