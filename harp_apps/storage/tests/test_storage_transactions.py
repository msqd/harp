from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageTransactions(StorageTestFixtureMixin):
    async def test_get_transaction_list_uses_a_single_session(self, sql_storage: SqlStorage):
        t1 = await self.create_transaction(sql_storage, endpoint="foo")
        t2 = await self.create_transaction(sql_storage, endpoint="bar")
        for t in (t1, t2):
            await self.create_message(sql_storage, transaction_id=t.id, kind="misc", summary="s", headers="h", body="b")

        calls = {"n": 0}
        original_begin = sql_storage.begin

        def counting_begin(*args, **kwargs):
            calls["n"] += 1
            return original_begin(*args, **kwargs)

        sql_storage.begin = counting_begin
        result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)

        # the count and the page are read in a single session/transaction
        assert calls["n"] == 1
        assert result.meta["total"] == 2
        assert len(result) == 2

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
