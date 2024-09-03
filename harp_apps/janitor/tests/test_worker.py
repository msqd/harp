from datetime import UTC, datetime, timedelta

import pytest

from harp_apps.janitor.settings import OLD_AFTER
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestJanitorWorker(StorageTestFixtureMixin):
    async def test_delete_old_transactions(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        worker = JanitorWorker(sql_storage, blob_storage)

        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(hours=1))
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(minutes=1))
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER + timedelta(minutes=1))

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await worker.delete_old_transactions()

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 1

    async def test_delete_orphan_blobs(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        if blob_storage.type == "redis":
            # explicit skip because it should be implemented later
            return pytest.skip("Redis implementation does not support cleaning up orphan blobs yet.")

        worker = JanitorWorker(sql_storage, blob_storage)

        b1 = await self.create_blob(blob_storage, "foo")
        b2 = await self.create_blob(blob_storage, "bar")
        await self.create_blob(blob_storage, "baz")

        async with sql_storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 3
            assert metrics["storage.blobs.orphans"] == 3

        t = await self.create_transaction(sql_storage)
        await self.create_message(
            sql_storage,
            transaction_id=t.id,
            kind="misc",
            summary="foo",
            headers=b1.id,
            body=b2.id,
        )

        async with sql_storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 3
            assert metrics["storage.blobs.orphans"] == 1

        await worker.delete_orphan_blobs()

        async with sql_storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 2
            assert metrics["storage.blobs.orphans"] == 0

    async def test_delete_old_transactions_but_keep_flagged_ones(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        worker = JanitorWorker(sql_storage, blob_storage)

        t1 = await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(hours=1))
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(minutes=1))
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - OLD_AFTER + timedelta(minutes=1))

        user = await sql_storage.users.find_one_by_username("anonymous")
        await sql_storage.flags.create({"type": 1, "user_id": user.id, "transaction_id": t1.id})

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await worker.delete_old_transactions()

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 2
