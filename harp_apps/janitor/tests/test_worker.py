import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from harp.models import Blob as BlobModel
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.tests import purge_old_transactions, worker_with_grace
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.models import Blob, Message
from harp_apps.storage.models.transactions import transaction_tag_values_association_table
from harp_apps.storage.models.metrics import MetricValue
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestJanitorWorker(StorageTestFixtureMixin):
    async def test_delete_old_transactions(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings())

        await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) - timedelta(hours=1)
        )
        await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) - timedelta(minutes=1)
        )
        await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) + timedelta(minutes=1)
        )

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await purge_old_transactions(sql_storage, worker.settings)

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 1

    async def test_retention_leaves_no_child_row_nor_blob(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))
        transaction = await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - timedelta(days=90))
        await sql_storage.transactions.set_tags(transaction, {"env": "tests"})
        headers = await self.create_blob(blob_storage, "headers")
        body = await self.create_blob(blob_storage, "body")
        await self.create_message(
            sql_storage, transaction_id=transaction.id, kind="misc", summary="x", headers=headers.id, body=body.id
        )

        await purge_old_transactions(sql_storage, worker.settings)
        await worker.delete_orphan_blobs()

        async with sql_storage.session_factory() as session:
            for model in (Message, transaction_tag_values_association_table, Blob):
                assert (await session.execute(select(func.count()).select_from(model))).scalar_one() == 0, model
        assert await blob_storage.get(headers.id) is None
        assert await blob_storage.get(body.id) is None

    async def test_compute_and_store_metrics(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """Runs on one connection: the in-memory default database has no second one to give (#995)."""
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings())
        await self.create_transaction(sql_storage)

        await asyncio.wait_for(worker.compute_and_store_metrics(), timeout=10)

        metric = await sql_storage.metrics.find_one({"name": "storage.transactions"})
        async with sql_storage.session_factory() as session:
            assert (await session.execute(select(MetricValue.value).filter_by(metric_id=metric.id))).scalar_one() == 1

    async def test_delete_orphan_blobs(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))

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

    async def test_a_swept_blob_can_be_written_again(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """A sweep must leave the blob storage able to store the same content again.

        The janitor deletes rows with its own SQL, so nothing tells `SqlBlobStorage` that they are
        gone. Its `seen` set is a claim that a row exists, and both `put()` and `exists()` trust it,
        so after a sweep every producer of content the janitor has already collected silently writes
        nothing at all, and the storage keeps reporting the blob as present.

        The pre-existing sweep test stops at the deletion. This one carries on to the write, which
        is where a cache, or anything else that stores blobs, meets the consequence.
        """

        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))

        blob = await self.create_blob(blob_storage, "swept")
        assert await blob_storage.get(blob.id) is not None
        assert await blob_storage.exists(blob.id) is True

        await worker.delete_orphan_blobs()
        assert await blob_storage.get(blob.id) is None, "the sweep should have removed it"
        assert await blob_storage.exists(blob.id) is False, "and it must not still be reported as present"

        await self.create_blob(blob_storage, "swept")
        assert await blob_storage.get(blob.id) is not None, "storing it again must actually store it"

    async def test_delete_old_transactions_but_keep_flagged_ones(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings())

        t1 = await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) - timedelta(hours=1)
        )
        await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) - timedelta(minutes=1)
        )
        await self.create_transaction(
            sql_storage, started_at=datetime.now(UTC) - timedelta(days=60) + timedelta(minutes=1)
        )

        user = await sql_storage.accounts.find_one_by_username("anonymous")
        await sql_storage.flags.create({"type": 1, "user_id": user.id, "transaction_id": t1.id})

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 3

        await purge_old_transactions(sql_storage, worker.settings)

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 2

    async def test_old_after_setting_drives_retention(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings(old_after=2))

        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - timedelta(days=3))
        await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - timedelta(days=1))

        await purge_old_transactions(sql_storage, worker.settings)

        async with sql_storage.session_factory() as session:
            assert (await worker.compute_metrics(session))["storage.transactions"] == 1

    async def test_period_setting_drives_sleep(self, sql_storage: SqlStorage, blob_storage: IBlobStorage, monkeypatch):
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings(period=7))
        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)
            worker.stop()

        async def noop():
            pass

        monkeypatch.setattr("harp_apps.janitor.worker.asyncio.sleep", fake_sleep)
        monkeypatch.setattr(worker, "loop", noop)

        await worker.run()

        assert sleeps == [7]


class TestRetentionKeepsSharedBlobs(StorageTestFixtureMixin):
    async def test_a_body_recorded_twice_outlives_the_first_expired_transaction(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))
        old = await self.create_transaction(sql_storage, started_at=datetime.now(UTC) - timedelta(days=90))
        recent = await self.create_transaction(sql_storage)
        headers = await self.create_blob(blob_storage, "headers")
        body = await self.create_blob(blob_storage, "same body")
        for transaction in (old, recent):
            await self.create_message(
                sql_storage, transaction_id=transaction.id, kind="misc", summary="x", headers=headers.id, body=body.id
            )

        await purge_old_transactions(sql_storage, worker.settings)
        await worker.delete_orphan_blobs()

        assert await blob_storage.get(body.id) == body
        assert await blob_storage.get(headers.id) == headers

    async def test_blobs_written_during_the_grace_period_are_kept(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        worker = JanitorWorker(sql_storage, blob_storage, JanitorSettings())
        young = await self.create_blob(blob_storage, "its message is not committed yet")

        await worker.delete_orphan_blobs()

        assert await blob_storage.get(young.id) is not None


class TestMetricsOfBlobStorage(StorageTestFixtureMixin):
    async def test_blob_figures_come_from_the_blob_storage_in_use(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))
        await self.create_blob(blob_storage, "one")
        await self.create_blob(blob_storage, "two")

        metrics = await worker.compute_metrics()

        assert metrics["storage.blobs"] == 2
        assert metrics["storage.blobs.orphans"] == 2


async def test_memory_blobs_are_swept_too(sql_storage: SqlStorage):
    from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

    blob_storage = MemoryBlobStorage()
    worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(0))
    orphan = await blob_storage.put(BlobModel.from_data("orphan"))

    assert (await worker.compute_metrics())["storage.blobs.orphans"] == 1
    await worker.delete_orphan_blobs()

    assert await blob_storage.get(orphan.id) is None
