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
