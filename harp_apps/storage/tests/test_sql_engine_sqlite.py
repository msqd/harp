import pytest
from pydantic_core import MultiHostUrl
from sqlalchemy import text

from harp_apps.storage.engines import SQLAlchemyEngine


async def pragma(engine, name):
    async with engine.connect() as connection:
        return (await connection.execute(text(f"PRAGMA {name}"))).scalar_one()


@pytest.fixture
async def file_engine(tmp_path):
    engine = SQLAlchemyEngine.from_url(MultiHostUrl(f"sqlite+aiosqlite:///{tmp_path}/harp.db"))
    yield engine
    await engine.dispose()


async def test_file_database_uses_write_ahead_log(file_engine):
    assert await pragma(file_engine, "journal_mode") == "wal"


async def test_file_database_does_not_sync_every_commit(file_engine):
    assert await pragma(file_engine, "synchronous") == 1  # NORMAL


async def test_file_database_waits_for_locks_before_failing(file_engine):
    assert await pragma(file_engine, "busy_timeout") == 10_000


async def test_every_pooled_connection_is_configured(file_engine):
    async with file_engine.connect() as first, file_engine.connect() as second:
        for connection in (first, second):
            assert (await connection.execute(text("PRAGMA busy_timeout"))).scalar_one() == 10_000


async def test_memory_database_keeps_its_journal():
    engine = SQLAlchemyEngine.from_url(MultiHostUrl("sqlite+aiosqlite:///:memory:?cache=shared"))
    try:
        assert await pragma(engine, "journal_mode") == "memory"
        assert await pragma(engine, "busy_timeout") != 10_000
    finally:
        await engine.dispose()


@pytest.mark.parametrize("url", ["postgresql+asyncpg://u:p@localhost/db", "mysql+aiomysql://u:p@localhost/db"])
def test_other_databases_get_no_sqlite_setup(url):
    engine = SQLAlchemyEngine.from_url(MultiHostUrl(url))
    assert not any("sqlite" in listener.__name__ for listener in engine.pool.dispatch.connect)


async def test_file_database_enforces_foreign_keys(file_engine):
    assert await pragma(file_engine, "foreign_keys") == 1


async def test_in_memory_database_enforces_foreign_keys():
    engine = SQLAlchemyEngine.from_url(MultiHostUrl("sqlite+aiosqlite:///:memory:"))
    try:
        assert await pragma(engine, "foreign_keys") == 1
    finally:
        await engine.dispose()
