"""A transaction keeps what the cache did for it (#404)."""

from datetime import UTC, datetime

from harp.models import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

CACHE_EXTRAS = dict(
    cache_outcome="revalidated",
    cache_key="http://api/items?" + "a" * 64,
    cache_variant="b" * 64,
    cache_seq=12,
    cache_age=30,
    cache_ttl=45,
)


def _transaction(**extras) -> Transaction:
    return Transaction(
        id=generate_transaction_id_ksuid(),
        type="http",
        started_at=datetime.now(UTC),
        endpoint="api",
        extras=extras,
    )


class TestStorageTransactionsCache(StorageTestFixtureMixin):
    @parametrize_with_database_urls()
    async def test_cache_outcome_is_stored_with_the_transaction(self, sql_storage: SqlStorage):
        transaction = _transaction(**CACHE_EXTRAS)
        await sql_storage.transactions.create(transaction)

        stored = await sql_storage.get_transaction(transaction.id, username="anonymous")

        assert {name: stored.extras[name] for name in CACHE_EXTRAS} == CACHE_EXTRAS

    @parametrize_with_database_urls()
    async def test_transaction_the_cache_did_not_see_has_no_outcome(self, sql_storage: SqlStorage):
        transaction = _transaction()
        await sql_storage.transactions.create(transaction)

        stored = await sql_storage.get_transaction(transaction.id, username="anonymous")

        assert "cache_outcome" not in stored.extras

    @parametrize_with_database_urls()
    async def test_transactions_are_filtered_by_cache_outcome(self, sql_storage: SqlStorage):
        outcomes = ("hit", "miss", "stale", None)
        for outcome in outcomes:
            await sql_storage.transactions.create(_transaction(cache_outcome=outcome))

        result = await sql_storage.get_transaction_list(username="anonymous", filters={"cache": ["hit", "stale"]})

        assert sorted(t.extras.get("cache_outcome") for t in result) == ["hit", "stale"]
