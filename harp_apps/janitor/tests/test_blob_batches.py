from datetime import timedelta

import pytest

from harp_apps.janitor.worker import JanitorWorker

from harp.models import Blob
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.tests import worker_with_grace
from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage
from harp_apps.storage.services.sql import SqlStorage

BATCH = 3
ORPHANS = 10


@pytest.fixture
def blob_storage(redis_blob_storage: RedisBlobStorage) -> RedisBlobStorage:
    """These tests are about Redis only: do not run them once more with the SQL blob storage."""
    return redis_blob_storage


@pytest.fixture
async def worker(sql_storage: SqlStorage, redis_blob_storage: RedisBlobStorage):
    worker = worker_with_grace(sql_storage, redis_blob_storage, JanitorSettings(), timedelta(0))
    worker.batch_size = BATCH
    for i in range(ORPHANS):
        await redis_blob_storage.put(Blob.from_data(f"orphan {i}"))
    return worker


async def test_orphans_are_deleted_in_bounded_batches(worker: JanitorWorker, redis_blob_storage, monkeypatch):
    sizes = []
    delete_stale = redis_blob_storage.delete_stale

    async def spy(blob_ids, /, **kwargs):
        blob_ids = list(blob_ids)
        sizes.append(len(blob_ids))
        return await delete_stale(blob_ids, **kwargs)

    monkeypatch.setattr(redis_blob_storage, "delete_stale", spy)

    await worker.delete_orphan_blobs()

    assert sum(sizes) == ORPHANS
    assert max(sizes) <= BATCH
    assert [i async for i in redis_blob_storage.iter_blob_ids()] == []


async def test_message_lookups_are_bounded_by_the_batch(worker: JanitorWorker, sql_storage, monkeypatch):
    sizes = []
    lookup = sql_storage.blobs.referenced_by_messages

    async def spy(blob_ids, /, **kwargs):
        sizes.append(len(blob_ids))
        return await lookup(blob_ids, **kwargs)

    monkeypatch.setattr(sql_storage.blobs, "referenced_by_messages", spy)

    await worker.delete_orphan_blobs()

    assert sizes and max(sizes) <= BATCH


async def test_a_loop_lists_blobs_once_for_cleanup_and_metrics(worker: JanitorWorker, redis_blob_storage, monkeypatch):
    scans = []
    scan_iter = redis_blob_storage.client.scan_iter

    def spy(*args, **kwargs):
        scans.append(kwargs.get("match"))
        return scan_iter(*args, **kwargs)

    monkeypatch.setattr(redis_blob_storage.client, "scan_iter", spy)

    await worker.loop()

    assert len(scans) == 2  # references of the cache entries, then the blobs: shared by cleanup and metrics


async def test_metrics_stored_by_a_loop_describe_what_is_left(worker: JanitorWorker, sql_storage, monkeypatch):
    stored = {}
    insert_values = sql_storage.metrics.insert_values

    async def spy(values, **kwargs):
        stored.update(values)
        return await insert_values(values, **kwargs)

    monkeypatch.setattr(sql_storage.metrics, "insert_values", spy)

    await worker.loop()

    assert stored["storage.blobs"] == 0
    assert stored["storage.blobs.orphans"] == 0


async def test_a_blob_listed_twice_by_scan_counts_once(worker: JanitorWorker, redis_blob_storage, monkeypatch):
    worker.batch_size = 2 * ORPHANS + 1
    iter_blob_ids = redis_blob_storage.iter_blob_ids

    async def twice():
        async for blob_id in iter_blob_ids():
            yield blob_id
            yield blob_id

    monkeypatch.setattr(redis_blob_storage, "iter_blob_ids", twice)

    values = await worker.compute_metrics()

    assert values["storage.blobs"] == ORPHANS
    assert values["storage.blobs.orphans"] == ORPHANS
