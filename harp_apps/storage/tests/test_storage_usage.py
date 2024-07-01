from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageUsage(StorageTestFixtureMixin):
    async def test_get_usage(self, storage: SqlStorage):
        usage = await storage.get_usage()
        assert usage == 0

        for i in range(3):
            await self.create_transaction(storage)

        usage = await storage.get_usage()
        assert usage == 3
