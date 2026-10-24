from datetime import UTC, datetime, timedelta

from harp.models import Blob
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage


async def test_delete_absent_key_is_a_noop():
    storage = MemoryBlobStorage()

    assert await storage.delete("absent") is None


async def test_delete_blobs_spares_a_blob_rewritten_since_and_ignores_absent_ones():
    storage = MemoryBlobStorage()
    old = Blob(id="rewritten", data=b"old", content_type="cache/meta")
    await storage.put(old)
    await storage.put(Blob(id="rewritten", data=b"fresh", content_type="cache/meta"))

    await storage.delete_blobs([old, Blob(id="absent", data=b"x", content_type="cache/meta")])

    assert (await storage.get("rewritten")).data == b"fresh"


async def test_iter_blob_ids_lists_every_blob():
    storage = MemoryBlobStorage()
    await storage.put(Blob(id="a", data=b"1"))
    await storage.put(Blob(id="b", data=b"2"))

    assert sorted([blob_id async for blob_id in storage.iter_blob_ids()]) == ["a", "b"]


async def test_delete_stale_deletes_blobs_not_written_since():
    storage = MemoryBlobStorage()
    await storage.put(Blob(id="a", data=b"1"))

    assert await storage.delete_stale(["a"], older_than=datetime.now(UTC) - timedelta(minutes=10)) == 0
    assert await storage.get("a") is not None

    assert await storage.delete_stale(["a", "absent"], older_than=datetime.now(UTC) + timedelta(seconds=1)) == 1
    assert await storage.get("a") is None
