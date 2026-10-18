from harp.settings import PAGE_SIZE
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestTransactionTextSearch(StorageTestFixtureMixin):
    async def create_exchange(self, sql_storage: SqlStorage, *, endpoint="/", summary="GET / 200"):
        transaction = await self.create_transaction(sql_storage, endpoint=endpoint)
        for kind in ("request", "response"):
            await self.create_message(
                sql_storage, transaction_id=transaction.id, kind=kind, summary=summary, headers="h", body="b"
            )
        return transaction

    async def test_total_and_pages_count_transactions_not_messages(self, sql_storage: SqlStorage):
        count = PAGE_SIZE + 10
        for _ in range(count):
            await self.create_exchange(sql_storage, endpoint="/billing", summary="billing")
        await self.create_exchange(sql_storage, endpoint="/other", summary="other")

        first = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="billing")
        second = await sql_storage.get_transaction_list(
            username="anonymous", with_messages=True, text_search="billing", page=2
        )

        assert first.meta["total"] == count
        assert len(first) == PAGE_SIZE
        assert len(second) == 10

    async def test_message_only_match_is_counted_once(self, sql_storage: SqlStorage):
        await self.create_exchange(sql_storage, endpoint="/a", summary="needle")
        await self.create_exchange(sql_storage, endpoint="/b", summary="hay")

        result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="needle")

        assert result.meta["total"] == 1
        assert len(result) == 1

    async def test_percent_matches_literally(self, sql_storage: SqlStorage):
        wanted = await self.create_exchange(sql_storage, endpoint="/100%25")
        await self.create_exchange(sql_storage, endpoint="/100abc")

        result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="100%")

        assert [t.id for t in result] == [wanted.id]
        assert result.meta["total"] == 1

    async def test_underscore_matches_literally(self, sql_storage: SqlStorage):
        wanted = await self.create_exchange(sql_storage, endpoint="/a_b")
        await self.create_exchange(sql_storage, endpoint="/axb")

        result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="a_b")

        assert [t.id for t in result] == [wanted.id]

    async def test_any_search_text_is_accepted(self, sql_storage: SqlStorage):
        await self.create_exchange(sql_storage)

        for search in ("%", "_", "\\", "'", '"', "+-*()<>~@^", "%%%"):
            result = await sql_storage.get_transaction_list(
                username="anonymous", with_messages=True, text_search=search
            )
            assert result.meta["total"] >= 0
