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
