import time
from datetime import UTC, datetime, timedelta
from unittest.mock import ANY

import pytest
from pydantic_core import MultiHostUrl
from sqlalchemy import delete, event, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection, async_sessionmaker

from harp.models import Blob
from harp_apps.storage.engines.sql_engine import SQLAlchemyEngine, create_async_engine
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.models.blobs import ORPHAN_GRACE, BlobsRepository
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


async def _age(engine, blob_id: str, age: timedelta):
    async with engine.connect() as conn:
        await conn.execute(
            update(SqlBlob).where(SqlBlob.id == blob_id).values(created_at=datetime.now(UTC) - age),
        )
        await conn.commit()


@pytest.fixture
async def server_behind_utc(sql_engine):
    """On MySQL, a server whose own timezone is behind UTC. Other backends are timezone-free."""
    if sql_engine.dialect.name != "mysql":
        yield
        return
    root = create_async_engine(sql_engine.url.set(username="root"))
    async with root.connect() as conn:
        previous = (await conn.execute(text("SELECT @@global.time_zone"))).scalar_one()
        await conn.execute(text("SET GLOBAL time_zone = '-08:00'"))
    await sql_engine.dispose()  # connections opened from now on see the new server timezone
    try:
        yield
    finally:
        async with root.connect() as conn:
            await conn.execute(text(f"SET GLOBAL time_zone = '{previous}'"))
        await root.dispose()


async def test_find_orphans_keeps_a_blob_younger_than_the_grace(server_behind_utc, sql_blob_storage: SqlBlobStorage):
    await sql_blob_storage.put(Blob(id="fresh", data=b"x", content_type="text/plain"))
    repository = BlobsRepository(async_sessionmaker(sql_blob_storage.engine))

    assert await repository.find_orphans(older_than=datetime.now(UTC) - ORPHAN_GRACE) == []
    assert await repository.find_orphans(older_than=datetime.now(UTC) + timedelta(minutes=1)) == ["fresh"]


async def test_put_renews_a_blob_the_janitor_sweeps_in_between(sql_blob_storage: SqlBlobStorage, monkeypatch):
    storage = sql_blob_storage
    await storage.put(Blob(id="old", data=b"x", content_type="text/plain"))
    await _age(storage.engine, "old", ORPHAN_GRACE * 2)

    swept = False
    original_execute = AsyncConnection.execute

    async def execute_then_sweep(self, *args, **kwargs):
        nonlocal swept
        result = await original_execute(self, *args, **kwargs)
        if not swept:  # the janitor runs right after put's first statement
            swept = True
            await original_execute(self, delete(SqlBlob).where(SqlBlob.created_at < datetime.now(UTC) - ORPHAN_GRACE))
            await self.commit()
        return result

    monkeypatch.setattr(AsyncConnection, "execute", execute_then_sweep)
    await storage.put(Blob(id="old", data=b"x", content_type="text/plain"))
    monkeypatch.undo()

    assert await storage.exists("old")


async def test_put_of_a_new_blob_needs_one_connection_at_a_time():
    engine = SQLAlchemyEngine.from_url(MultiHostUrl("sqlite+aiosqlite:///:memory:"))  # a pool of one
    async with engine.begin() as conn:
        await conn.run_sync(SqlBlob.metadata.create_all)
    try:
        started = time.monotonic()
        await SqlBlobStorage(engine).put(Blob(id="new", data=b"x", content_type="text/plain"))
        assert time.monotonic() - started < 2
    finally:
        await engine.dispose()


async def test_put_in_stores_missing_blobs_and_leaves_existing_ones(sql_blob_storage: SqlBlobStorage):
    storage = sql_blob_storage
    await storage.put(Blob(id="there", data=b"first", content_type="text/plain"))

    async with storage.engine.begin() as conn:
        await storage.put_in(
            conn,
            [
                Blob(id="there", data=b"other", content_type="text/plain"),
                Blob(id="new", data=b"new", content_type=None),
            ],
        )

    assert (await storage.get("there")).data == b"first"
    assert (await storage.get("new")).data == b"new"


async def test_put_in_renews_old_blobs_in_the_callers_transaction(sql_blob_storage: SqlBlobStorage):
    storage = sql_blob_storage
    await storage.put(Blob(id="old", data=b"x", content_type="text/plain"))
    await _age(storage.engine, "old", ORPHAN_GRACE * 2)

    async with storage.engine.connect() as conn:
        await storage.put_in(conn, [Blob(id="old", data=b"x", content_type="text/plain")])
        await conn.rollback()  # nothing committed: the renewal belongs to the caller's transaction

    async with storage.engine.connect() as conn:
        created_at = (await conn.execute(select(SqlBlob.created_at).where(SqlBlob.id == "old"))).scalar_one()
    assert created_at.replace(tzinfo=UTC) < datetime.now(UTC) - ORPHAN_GRACE

    async with storage.engine.begin() as conn:
        await storage.put_in(conn, [Blob(id="old", data=b"x", content_type="text/plain")])

    async with storage.engine.connect() as conn:
        created_at = (await conn.execute(select(SqlBlob.created_at).where(SqlBlob.id == "old"))).scalar_one()
    assert created_at.replace(tzinfo=UTC) > datetime.now(UTC) - ORPHAN_GRACE / 2


async def test_put_in_with_nothing_does_nothing(sql_blob_storage: SqlBlobStorage):
    async with sql_blob_storage.engine.begin() as conn:
        await sql_blob_storage.put_in(conn, [])
