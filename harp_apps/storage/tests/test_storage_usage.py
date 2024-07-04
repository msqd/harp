from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageUsage(StorageTestFixtureMixin):
    async def test_get_usage(self, sql_storage: SqlStorage):
        usage = await sql_storage.get_usage()
        assert usage == 0

        for i in range(3):
            await self.create_transaction(sql_storage)

        usage = await sql_storage.get_usage()
        assert usage == 3
