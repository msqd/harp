from datetime import UTC, datetime

import pytest
from whistle import AsyncEventDispatcher

from harp.core.models import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage


class SqlalchemyStorageTestFixtureMixin:
    storage_settings = {
        "url": "sqlite+aiosqlite:///:memory:",
        "echo": False,
    }

    async def create_storage(self, /, *, dispatcher=None, **settings) -> SqlAlchemyStorage:
        storage = SqlAlchemyStorage(
            dispatcher=dispatcher or AsyncEventDispatcher(),
            settings=SqlAlchemyStorageSettings(**{**self.storage_settings, **settings}),
        )

        # todo wrap the test in a transaction ?
        await storage.initialize(force_reset=True)
        await storage.create_users(["anonymous"])

        return storage

    @pytest.fixture
    async def storage(self, database_url):
        yield await self.create_storage(url=database_url)

    async def create_transaction(self, storage: SqlAlchemyStorage, **kwargs):
        return await storage.create_transaction(
            Transaction(
                **{
                    **{
                        "id": generate_transaction_id_ksuid(),
                        "type": "http",
                        "endpoint": "/",
                        "started_at": datetime.now(UTC).replace(tzinfo=None),
                    },
                    **kwargs,
                }
            )
        )