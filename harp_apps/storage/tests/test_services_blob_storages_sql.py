from unittest.mock import ANY

from sqlalchemy import event, text

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


async def test_iter_blobs_holds_no_connection_between_batches(sql_blob_storage: SqlBlobStorage):
    for i in range(450):
        await sql_blob_storage.put(Blob(id=f"blob-{i:04}", data=b"x", content_type="cache/meta"))
    await sql_blob_storage.put(Blob(id="other", data=b"x", content_type="text/plain"))

    in_use = 0

    def checked_out(*_):
        nonlocal in_use
        in_use += 1

    def checked_in(*_):
        nonlocal in_use
        in_use -= 1

    pool = sql_blob_storage.engine.sync_engine.pool
    event.listen(pool, "checkout", checked_out)
    event.listen(pool, "checkin", checked_in)

    seen = []
    in_use_when_paused = set()
    async for blob in sql_blob_storage.iter_blobs("cache/meta"):
        seen.append(blob.id)
        in_use_when_paused.add(in_use)

    assert seen == [f"blob-{i:04}" for i in range(450)]
    assert in_use_when_paused == {0}


async def test_delete_blobs_removes_chunks_in_one_statement_and_transaction_each(sql_blob_storage: SqlBlobStorage):
    blobs = [Blob(id=f"blob-{i:04}", data=b"x", content_type="cache/meta") for i in range(450)]
    for blob in blobs:
        await sql_blob_storage.put(blob)

    statements = []
    commits = []
    sync_engine = sql_blob_storage.engine.sync_engine
    event.listen(
        sync_engine,
        "before_cursor_execute",
        lambda *args: statements.append(args[2]) if args[2].startswith("DELETE") else None,
    )
    event.listen(sync_engine, "commit", lambda *_: commits.append(1))

    await sql_blob_storage.delete_blobs(blobs)

    assert [b async for b in sql_blob_storage.iter_blobs("cache/meta")] == []
    assert len(statements) == len(commits) == 3  # 200 + 200 + 50


async def test_delete_blobs_spares_a_blob_rewritten_since_and_ignores_absent_ones(sql_blob_storage: SqlBlobStorage):
    old = Blob(id="rewritten", data=b"old", content_type="cache/meta")
    await sql_blob_storage.put(old)
    await sql_blob_storage.force_put(Blob(id="rewritten", data=b"fresh", content_type="cache/meta"))

    await sql_blob_storage.delete_blobs([old, Blob(id="absent", data=b"x", content_type="cache/meta")])

    assert (await sql_blob_storage.get("rewritten")).data == b"fresh"
