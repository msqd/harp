"""The janitor and the HTTP cache share one blobs table.

A cache entry is a ``cache/meta`` blob pointing at header and body blobs that are content-addressed,
and shared with message blobs. Only the ``cache/meta`` blob says which of them the cache still uses,
so the janitor has to follow those references before calling anything an orphan.
"""

from datetime import UTC, datetime, timedelta

import pytest
from hishel import Headers, Request, Response
from hishel._core.models import AnyIterable
from sqlalchemy import update

from harp.models import Blob
from harp_apps.http_cache.tests import store_entry
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.tests import worker_with_grace
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

NO_GRACE = timedelta(0)


def _request(url="http://endpoint/resource"):
    return Request(method="GET", url=url, headers=Headers({"accept": "text/plain"}))


def _response(body=b"payload"):
    return Response(
        status_code=200,
        headers=Headers({"cache-control": "max-age=3600", "content-type": "text/plain"}),
        stream=AnyIterable(body),
        metadata={},
    )


@pytest.fixture
def sql_only(blob_storage: IBlobStorage):
    if blob_storage.type != "sql":
        pytest.skip("The janitor only sweeps SQL blob storage.")


@pytest.mark.usefixtures("sql_only")
class TestJanitorAndHttpCache(StorageTestFixtureMixin):
    @pytest.fixture
    def worker(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        return worker_with_grace(sql_storage, blob_storage, JanitorSettings(), NO_GRACE)

    @pytest.fixture
    def cache(self, blob_storage: IBlobStorage):
        return AsyncStorage(blob_storage)

    async def orphans(self, worker: JanitorWorker, sql_storage: SqlStorage):
        async with sql_storage.session_factory() as session:
            return (await worker.compute_metrics(session))["storage.blobs.orphans"]

    async def test_cached_entry_survives_janitor_passes(self, worker, cache):
        await store_entry(cache, _request(), _response(), "key-1")

        for _ in range(3):
            await worker.delete_orphan_blobs()

        (entry,) = await cache.get_entries("key-1")
        assert await entry.response.aread() == b"payload"

    async def test_cache_blobs_are_not_counted_as_orphans(self, worker, cache, sql_storage, blob_storage):
        await store_entry(cache, _request(), _response(), "key-1")
        assert await self.orphans(worker, sql_storage) == 0

        await self.create_blob(blob_storage, "referenced by nothing")
        assert await self.orphans(worker, sql_storage) == 1

    async def test_blobs_of_a_replaced_entry_are_reclaimed(self, worker, cache, blob_storage):
        await store_entry(cache, _request(), _response(b"old"), "key-1")
        old_body = Blob.from_data(b"old", content_type="text/plain")
        assert await blob_storage.get(old_body.id) is not None

        await store_entry(cache, _request(), _response(b"new"), "key-1")
        await worker.delete_orphan_blobs()

        assert await blob_storage.get(old_body.id) is None
        assert await blob_storage.get(Blob.from_data(b"new", content_type="text/plain").id) is not None

    async def test_blob_shared_with_a_message_outlives_the_cache_entry(self, worker, cache, blob_storage, sql_storage):
        await store_entry(cache, _request(), _response(b"shared"), "key-1")
        shared = Blob.from_data(b"shared", content_type="text/plain")
        t = await self.create_transaction(sql_storage)
        await self.create_message(
            sql_storage, transaction_id=t.id, kind="misc", summary="x", headers="h", body=shared.id
        )

        await blob_storage.delete("key-1")
        await worker.delete_orphan_blobs()

        assert await blob_storage.get(shared.id) is not None

    async def test_unreferenced_cache_meta_is_never_an_orphan(self, worker, blob_storage):
        """Cache storage is reclaimed by the TTL sweep, not by the janitor."""
        await blob_storage.force_put(Blob(id="k", data=b"not even yaml: [", content_type="cache/meta"))

        await worker.delete_orphan_blobs()

        assert await blob_storage.get("k") is not None


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
