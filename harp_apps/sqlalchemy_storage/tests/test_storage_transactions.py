from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestStorageTransactions(SqlalchemyStorageTestFixtureMixin):
    async def test_get_transaction_list_with_tags(self, storage: SqlAlchemyStorage):
        t1 = await self.create_transaction(storage, endpoint="foo")

        t2 = await self.create_transaction(storage, endpoint="bar")

        t3 = await self.create_transaction(storage, endpoint="baz")

        # messages
        await self.create_message(storage, transaction_id=t1.id, kind="misc", summary="bal", headers="foo", body="foo")
        await self.create_message(storage, transaction_id=t2.id, kind="misc", summary="foo", headers="bar", body="baz")
        await self.create_message(storage, transaction_id=t3.id, kind="misc", summary="baz", headers="baz", body="baz")

        # assert stuff
        transactions_bar = await storage.get_transaction_list(
            username="anonymous", with_messages=True, text_search="bar"
        )
        assert len(transactions_bar) == 1

        assert transactions_bar[0].id == t2.id

        transactions_fo = await storage.get_transaction_list(username="anonymous", with_messages=True, text_search="fo")
        assert len(transactions_fo) == 2

        transactions_ba = await storage.get_transaction_list(username="anonymous", with_messages=True, text_search="ba")
        assert len(transactions_ba) == 3
