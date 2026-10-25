"""The janitor and the HTTP cache of earlier versions.

That cache was ``cache/meta`` blobs pointing at header and body blobs, which the janitor had to follow before calling
anything an orphan. The cache now keeps its records in tables of their own (ADR-0014) and drops what the earlier
one left: nothing reads those blobs anymore, so the janitor reclaims them like any blob nothing references.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from harp.models import Blob
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.tests import worker_with_grace
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

NO_GRACE = timedelta(0)


@pytest.fixture
def sql_only(blob_storage: IBlobStorage):
    if blob_storage.type != "sql":
        pytest.skip("The janitor only sweeps SQL blob storage.")


class TestJanitorAndTheCacheOfEarlierVersions(StorageTestFixtureMixin):
    @pytest.fixture
    def worker(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        return worker_with_grace(sql_storage, blob_storage, JanitorSettings(), NO_GRACE)

    async def test_the_blobs_of_an_old_cache_entry_are_reclaimed(self, worker, blob_storage):
        headers = await blob_storage.put(Blob.from_data(b"accept: */*", content_type="http/headers"))
        body = await blob_storage.put(Blob.from_data(b"payload", content_type="text/plain"))
        meta = (
            f"variants:\n- request: {{headers: {headers.id}}}\n  response: {{headers: {headers.id}, body: {body.id}}}\n"
        )
        await blob_storage.force_put(Blob(id="k", data=meta.encode(), content_type="cache/meta"))

        await worker.delete_orphan_blobs()

        assert [await blob_storage.get(blob_id) for blob_id in ("k", headers.id, body.id)] == [None, None, None]

    async def test_an_unreadable_cache_entry_is_reclaimed_too(self, worker, blob_storage):
        await blob_storage.force_put(Blob(id="k", data=b"not even yaml: [", content_type="cache/meta"))

        await worker.delete_orphan_blobs()

        assert await blob_storage.get("k") is None


@pytest.mark.usefixtures("sql_only")
class TestOrphanGrace(StorageTestFixtureMixin):
    async def age(self, sql_storage: SqlStorage, blob_id: str, by: timedelta):
        async with sql_storage.session_factory() as session:
            await session.execute(
                update(SqlBlob).where(SqlBlob.id == blob_id).values(created_at=datetime.now(UTC) - by)
            )
            await session.commit()

    async def test_young_orphans_are_kept(self, sql_storage, blob_storage):
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(minutes=10))
        young = await self.create_blob(blob_storage, "young")
        old = await self.create_blob(blob_storage, "old")
        await self.age(sql_storage, old.id, timedelta(minutes=11))

        await worker.delete_orphan_blobs()

        assert await blob_storage.get(young.id) is not None, "its message may not be committed yet"
        assert await blob_storage.get(old.id) is None

    async def test_putting_an_old_blob_again_protects_it_from_the_next_sweep(self, sql_storage, blob_storage):
        """Single process window: a producer finds the content already stored, then the sweep runs
        before its message commits."""
        worker = worker_with_grace(sql_storage, blob_storage, JanitorSettings(), timedelta(minutes=10))
        blob = await self.create_blob(blob_storage, "reused")
        await self.age(sql_storage, blob.id, timedelta(hours=3))

        await self.create_blob(blob_storage, "reused")
        await worker.delete_orphan_blobs()

        assert await blob_storage.get(blob.id) is not None


class TestBlobStorageSharedByInstances(StorageTestFixtureMixin):
    async def test_blob_swept_by_another_instance_is_written_again(self, sql_storage, sql_engine, blob_storage):
        if blob_storage.type != "sql":
            pytest.skip("sql only")
        a, b = blob_storage, SqlBlobStorage(sql_engine)
        worker = worker_with_grace(sql_storage, a, JanitorSettings(), NO_GRACE)

        x = await self.create_blob(a, "x")
        await self.create_blob(b, "x")

        await worker.delete_orphan_blobs()
        await self.create_blob(b, "x")
        t = await self.create_transaction(sql_storage)
        await self.create_message(sql_storage, transaction_id=t.id, kind="misc", summary="x", headers="h", body=x.id)

        assert await b.get(x.id) is not None
