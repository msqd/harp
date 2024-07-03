from harp.models import Blob
from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage


async def test_basics(redis_blob_storage: RedisBlobStorage):
    _storage = redis_blob_storage
    assert _storage.client is not None
    blob = Blob(id="foo", data=b"bar", content_type="text/plain")

    assert _storage.type == "redis"
    assert await _storage.get("foo") is None
    assert await _storage.client.get("foo") is None

    assert await _storage.put(blob) == blob
    assert await _storage.get("foo") == blob
    assert await _storage.client.get("foo") == b"text/plain\nbar"

    assert await _storage.exists("foo")
    assert await _storage.delete("foo") is None
    assert not await _storage.exists("foo")
    assert await _storage.get("foo") is None
    assert await _storage.client.get("foo") is None
