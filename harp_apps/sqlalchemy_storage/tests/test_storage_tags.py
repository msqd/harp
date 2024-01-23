from datetime import UTC, datetime

from harp.core.models.transactions import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestStorageTags(SqlalchemyStorageTestFixtureMixin):
    echo = False

    async def test_get_transaction_list_with_tags(self, storage: SqlAlchemyStorage):
        t1 = await storage.create_transaction(
            Transaction(
                id=generate_transaction_id_ksuid(),
                type="http",
                endpoint="/api/transactions",
                started_at=datetime.now(UTC),
            )
        )

        tags = {"version": "42", "env": "tests"}

        # set some tags
        await storage.set_transaction_tags(t1.id, tags)

        # refresh our transaction from db (test env allow us to do this)
        t1_again = await storage.transactions.find_one_by_id(t1.id, with_tags=True)

        # internal api returns 2 tags
        assert (len(t1_again._tag_values)) == 2

        # ... that we can read using our convenience api
        assert t1_again.tags == tags
