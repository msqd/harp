from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageTags(StorageTestFixtureMixin):
    async def test_get_transaction_list_with_tags(self, sql_storage: SqlStorage):
        t1 = await self.create_transaction(sql_storage)

        tags = {"version": "42", "env": "tests"}

        # set some tags
        await sql_storage.transactions.set_tags(t1, tags)

        # refresh our transaction from db (test env allow us to do this)
        t1_again = await sql_storage.transactions.find_one_by_id(t1.id, with_tags=True)

        # internal api returns 2 tags
        assert (len(t1_again._tag_values)) == 2

        # ... that we can read using our convenience api
        assert t1_again.tags == tags

    @parametrize_with_database_urls()
    async def test_tag_at_the_column_widths_is_stored(self, sql_storage: SqlStorage):
        t1 = await self.create_transaction(sql_storage)
        tags = {"n" * 64: "v" * 255}

        await sql_storage.transactions.set_tags(t1, tags)

        assert (await sql_storage.transactions.find_one_by_id(t1.id, with_tags=True)).tags == tags
