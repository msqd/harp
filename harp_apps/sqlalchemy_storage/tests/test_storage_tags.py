from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestStorageTags(SqlalchemyStorageTestFixtureMixin):
    async def test_get_transaction_list_with_tags(self, storage: SqlAlchemyStorage):
        t1 = await self.create_transaction(storage)

        tags = {"version": "42", "env": "tests"}

        # set some tags
        await storage.transactions.set_tags(t1, tags)

        # refresh our transaction from db (test env allow us to do this)
        t1_again = await storage.transactions.find_one_by_id(t1.id, with_tags=True)

        # internal api returns 2 tags
        assert (len(t1_again._tag_values)) == 2

        # ... that we can read using our convenience api
        assert t1_again.tags == tags
