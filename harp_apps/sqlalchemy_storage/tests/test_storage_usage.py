from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestStorageUsage(SqlalchemyStorageTestFixtureMixin):
    async def test_get_usage(self, storage: SqlAlchemyStorage):
        usage = await storage.get_usage()
        assert usage == 0

        for i in range(3):
            await self.create_transaction(storage)

        usage = await storage.get_usage()
        assert usage == 3
