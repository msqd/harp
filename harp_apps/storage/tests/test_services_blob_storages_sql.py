from unittest.mock import ANY

from sqlalchemy import text

from harp.models import Blob
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage


async def test_basics(sql_blob_storage: SqlBlobStorage):
    _storage = sql_blob_storage
    blob = Blob(id="foo", data=b"bar", content_type="text/plain")

    assert _storage.type == "sql"
    assert await _storage.get("foo") is None
    async with _storage.engine.connect() as conn:
        assert (await conn.execute(text("SELECT * FROM blobs WHERE id = 'foo'"))).fetchone() is None

    assert await _storage.put(blob) == blob
    assert await _storage.get("foo") == blob
    async with _storage.engine.connect() as conn:
        assert (
            await conn.execute(
                text("SELECT * FROM blobs WHERE id = 'foo'"),
            )
        ).fetchone() == ("foo", b"bar", "text/plain", ANY)

    assert await _storage.exists("foo")
    assert await _storage.delete("foo") is None
    assert not await _storage.exists("foo")
    assert await _storage.get("foo") is None
    async with _storage.engine.connect() as conn:
        assert (await conn.execute(text("SELECT * FROM blobs WHERE id = 'foo'"))).fetchone() is None


async def test_put_populates_seen_cache(sql_blob_storage: SqlBlobStorage):
    # After a put, the blob id is known to be stored, so it must be cached to let later puts skip
    # the existence query.
    storage = sql_blob_storage
    assert not storage.seen.exists("foo")
    await storage.put(Blob(id="foo", data=b"bar", content_type="text/plain"))
    assert storage.seen.exists("foo")


async def test_exists_populates_seen_cache(sql_blob_storage: SqlBlobStorage):
    # A positive existence check must also seed the cache. force_put does not touch the cache, so it
    # gives us a stored-but-uncached blob.
    storage = sql_blob_storage
    await storage.force_put(Blob(id="foo", data=b"bar", content_type="text/plain"))
    assert not storage.seen.exists("foo")
    assert await storage.exists("foo")
    assert storage.seen.exists("foo")
