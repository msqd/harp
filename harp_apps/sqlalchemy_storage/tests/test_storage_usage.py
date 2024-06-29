from harp_apps.sqlalchemy_storage.storages.sql import SqlStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestStorageUsage(SqlalchemyStorageTestFixtureMixin):
    async def test_get_usage(self, storage: SqlStorage):
        usage = await storage.get_usage()
        assert usage == 0

        for i in range(3):
            await self.create_transaction(storage)

        usage = await storage.get_usage()
        assert usage == 3
