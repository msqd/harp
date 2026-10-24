import sqlite3
from functools import partial

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from harp_apps.storage.models import Base
from harp_apps.storage.utils.migrations import (
    OutdatedSchemaError,
    create_alembic_config,
    ensure_schema_is_current,
)


async def _create_sqlite_file(path, *, drop_transactions_markers=False):
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    if drop_transactions_markers:
        # shape of a file written by 0.11, before transactions.markers
        with sqlite3.connect(path) as conn:
            conn.execute("ALTER TABLE transactions DROP COLUMN markers")


async def test_current_sqlite_file_is_accepted(tmp_path):
    path = tmp_path / "current.db"
    await _create_sqlite_file(path)

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    await ensure_schema_is_current(engine)
    await engine.dispose()


async def test_0_11_sqlite_file_is_refused_with_options(tmp_path):
    path = tmp_path / "old.db"
    await _create_sqlite_file(path, drop_transactions_markers=True)

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    with pytest.raises(OutdatedSchemaError) as exc_info:
        await ensure_schema_is_current(engine)
    await engine.dispose()

    message = str(exc_info.value)
    assert str(path) in message
    assert "outdated" in message
    assert "transactions.markers" in message
    assert f"rm {path}" in message
    assert f"harp-proxy db:reset --set storage.url=sqlite+aiosqlite:///{path}" in message


async def test_database_behind_alembic_head_is_refused(sql_engine):
    if sql_engine.dialect.name == "sqlite":
        pytest.skip("sqlite schema is checked against the models, not alembic")

    await ensure_schema_is_current(sql_engine)

    alembic_cfg = create_alembic_config(sql_engine.url.render_as_string(hide_password=False))
    from concurrent.futures import ThreadPoolExecutor
    import asyncio

    with ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(executor, partial(command.downgrade, alembic_cfg, "-1"))

    with pytest.raises(OutdatedSchemaError) as exc_info:
        await ensure_schema_is_current(sql_engine)

    assert "outdated" in str(exc_info.value)
    assert "harp-proxy db:migrate up head --set storage.url=" in str(exc_info.value)


async def _build_system(path):
    from harp.config import ConfigurationBuilder

    settings = {"applications": ["storage"], "storage": {"url": f"sqlite+aiosqlite:///{path}"}}
    return await ConfigurationBuilder(settings, use_default_applications=False).abuild_system(
        validate_dependencies=False
    )


async def test_startup_refuses_0_11_sqlite_file(tmp_path):
    path = tmp_path / "old.db"
    await _create_sqlite_file(path, drop_transactions_markers=True)

    with pytest.raises(OutdatedSchemaError, match="outdated"):
        await _build_system(path)


async def test_startup_accepts_current_sqlite_file(tmp_path):
    path = tmp_path / "current.db"
    await _create_sqlite_file(path)

    system = await _build_system(path)
    await system.dispose()
