from datetime import UTC, datetime, timedelta

from harp_apps.janitor.settings import OLD_AFTER
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin


class TestJanitorWorker(SqlalchemyStorageTestFixtureMixin):
    async def test_delete_old_transactions(self, storage: SqlAlchemyStorage):
        worker = JanitorWorker(storage)

        await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(hours=1))
        await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(minutes=1))
        await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER + timedelta(minutes=1))

        async with storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await worker.delete_old_transactions()

        async with storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 1

    async def test_delete_orphan_blobs(self, storage: SqlAlchemyStorage):
        worker = JanitorWorker(storage)

        b1 = await self.create_blob(storage, "foo")
        b2 = await self.create_blob(storage, "bar")
        await self.create_blob(storage, "baz")

        async with storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 3
            assert metrics["storage.blobs.orphans"] == 3

        t = await self.create_transaction(storage)
        await self.create_message(storage, transaction_id=t.id, kind="misc", summary="foo", headers=b1.id, body=b2.id)

        async with storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 3
            assert metrics["storage.blobs.orphans"] == 1

        await worker.delete_orphan_blobs()

        async with storage.session_factory() as session:
            metrics = await worker.compute_metrics(session)
            assert metrics["storage.blobs"] == 2
            assert metrics["storage.blobs.orphans"] == 0

    async def test_delete_old_transactions_but_keep_flagged_ones(self, storage: SqlAlchemyStorage):
        worker = JanitorWorker(storage)

        t1 = await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(hours=1))
        await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER - timedelta(minutes=1))
        await self.create_transaction(storage, started_at=datetime.now(UTC) - OLD_AFTER + timedelta(minutes=1))

        user = await storage.users.find_one_by_username("anonymous")
        await storage.flags.create({"type": 1, "user_id": user.id, "transaction_id": t1.id})

        async with storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await worker.delete_old_transactions()

        async with storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 2
