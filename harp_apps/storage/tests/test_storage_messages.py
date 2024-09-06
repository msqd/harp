from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageMessages(StorageTestFixtureMixin):
    async def test_create_message(self, sql_storage):
        transaction = await self.create_transaction(sql_storage)
        message = await self.create_message(
            sql_storage, transaction_id=transaction.id, kind="misc", summary="bal", headers="foo", body="foo"
        )
        assert message.id is not None
        assert message.transaction_id == transaction.id
        assert message.kind == "misc"
        assert message.summary == "bal"
        assert message.headers == "foo"
        assert message.body == "foo"

    async def test_create_message_with_long_summary(self, sql_storage):
        transaction = await self.create_transaction(sql_storage)
        message = await self.create_message(
            sql_storage, transaction_id=transaction.id, kind="misc", summary="a" * 500, headers="foo", body="foo"
        )
        assert message.id is not None
        assert message.transaction_id == transaction.id
        assert message.kind == "misc"
        assert message.summary == "a" * 500
        assert message.headers == "foo"
        assert message.body == "foo"
