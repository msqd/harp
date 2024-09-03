from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageTransactions(StorageTestFixtureMixin):
    async def test_get_transaction_list_with_tags(self, sql_storage: SqlStorage):
        t1 = await self.create_transaction(sql_storage, endpoint="foo")

        t2 = await self.create_transaction(sql_storage, endpoint="bar")

        t3 = await self.create_transaction(sql_storage, endpoint="baz")

        # messages
        await self.create_message(
            sql_storage,
            transaction_id=t1.id,
            kind="misc",
            summary="bal",
            headers="foo",
            body="foo",
        )
        await self.create_message(
            sql_storage,
            transaction_id=t2.id,
            kind="misc",
            summary="foo",
            headers="bar",
            body="baz",
        )
        await self.create_message(
            sql_storage,
            transaction_id=t3.id,
            kind="misc",
            summary="baz",
            headers="baz",
            body="baz",
        )

        # assert stuff
        transactions_bar = await sql_storage.get_transaction_list(
            username="anonymous", with_messages=True, text_search="bar"
        )
        assert len(transactions_bar) == 1

        assert transactions_bar[0].id == t2.id

        transactions_fo = await sql_storage.get_transaction_list(
            username="anonymous", with_messages=True, text_search="fo"
        )
        assert len(transactions_fo) == 2

        transactions_ba = await sql_storage.get_transaction_list(
            username="anonymous", with_messages=True, text_search="ba"
        )
        assert len(transactions_ba) == 3
