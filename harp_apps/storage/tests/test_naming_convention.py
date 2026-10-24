"""
Every constraint of the storage schema has a name, and the name follows the naming convention of ``Base.metadata``.

SQLite batch migrations can only alter a constraint they can name, so renaming ``users`` or any later table change
depends on it. The schema reached by ``Base.metadata.create_all``, the one reached by the alembic chain and the one
reached by the naming migration from a 0.12 schema must all carry the same names.
"""

import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import pytest
from alembic import command
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.models import Base
from harp_apps.storage.utils.migrations import create_alembic_config, ensure_schema_is_current
from harp_apps.storage.utils.testing.sql import get_scoped_database_url

NAMING_REVISION = "e7a4d9c26b18"
PREVIOUS_REVISION = "c5e8b2d41f73"

# Duplicated unique constraints that migrations 248285939c4c and d4cd37d29d7a stacked on PostgreSQL and MySQL.
# SQLite files and ``create_all`` never had them: the naming migration keeps one of each.
STACKED_DUPLICATES = {"id_2", "__values_uc"}

# What ``Base.metadata.create_all`` wrote in a SQLite file before constraints were named (0.12).
LEGACY_SQLITE_SCHEMA = """
CREATE TABLE blobs (
    id VARCHAR(64) NOT NULL, data BLOB, content_type VARCHAR(64), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id), UNIQUE (id)
);
CREATE TABLE metrics (
    id INTEGER NOT NULL, name VARCHAR(255) NOT NULL, PRIMARY KEY (id), UNIQUE (id), UNIQUE (name)
);
CREATE TABLE tags (
    id INTEGER NOT NULL, name VARCHAR(64) NOT NULL, PRIMARY KEY (id), UNIQUE (id), UNIQUE (name)
);
CREATE TABLE transactions (
    id VARCHAR(27) NOT NULL, type VARCHAR(10) NOT NULL, endpoint VARCHAR(32), started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP, elapsed FLOAT, tpdex INTEGER, x_method VARCHAR(16), x_status_class VARCHAR(3),
    x_cached VARCHAR(32), x_no_cache BOOLEAN, markers TEXT, PRIMARY KEY (id), UNIQUE (id)
);
CREATE INDEX ix_transactions_type ON transactions (type);
CREATE INDEX ix_transactions_started_at ON transactions (started_at);
CREATE INDEX ix_transactions_endpoint ON transactions (endpoint);
CREATE INDEX ix_transactions_x_method ON transactions (x_method);
CREATE INDEX ix_transactions_x_status_class ON transactions (x_status_class);
CREATE TABLE users (
    id INTEGER NOT NULL, username VARCHAR(32), PRIMARY KEY (id), UNIQUE (id), UNIQUE (username)
);
CREATE TABLE messages (
    id INTEGER NOT NULL, kind VARCHAR(10) NOT NULL, summary TEXT NOT NULL, headers VARCHAR(40), body VARCHAR(40),
    created_at TIMESTAMP NOT NULL, transaction_id VARCHAR(27) NOT NULL, PRIMARY KEY (id), UNIQUE (id),
    FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
);
CREATE INDEX ix_transaction_id ON messages (transaction_id);
CREATE TABLE trans_user_flags (
    id INTEGER NOT NULL, type INTEGER NOT NULL, user_id INTEGER NOT NULL, transaction_id VARCHAR(27) NOT NULL,
    PRIMARY KEY (id), CONSTRAINT _user_transaction_uc UNIQUE (user_id, transaction_id, type), UNIQUE (id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
);
CREATE TABLE metric_values (
    metric_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, value INTEGER,
    PRIMARY KEY (metric_id, created_at), FOREIGN KEY(metric_id) REFERENCES metrics (id)
);
CREATE TABLE tag_values (
    id INTEGER NOT NULL, tag_id INTEGER NOT NULL, value VARCHAR(255) NOT NULL, PRIMARY KEY (id),
    CONSTRAINT __values_uc UNIQUE (tag_id, value), UNIQUE (id),
    FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
);
CREATE TABLE trans_tag_values (
    transaction_id VARCHAR(27) NOT NULL, value_id INTEGER NOT NULL, PRIMARY KEY (transaction_id, value_id),
    FOREIGN KEY(transaction_id) REFERENCES transactions (id) ON DELETE CASCADE,
    FOREIGN KEY(value_id) REFERENCES tag_values (id) ON DELETE CASCADE
);
"""


def constraint_names(sync_conn) -> dict:
    """Name of every primary key, unique constraint, foreign key and ``ix_*`` index, by what it constrains."""
    inspector = inspect(sync_conn)
    names = {}
    for table in inspector.get_table_names():
        if table == "alembic_version":
            continue
        # MySQL has no name for a primary key
        if sync_conn.dialect.name != "mysql":
            names[(table, "pk", tuple(inspector.get_pk_constraint(table)["constrained_columns"]))] = (
                inspector.get_pk_constraint(table)["name"]
            )
        for unique in inspector.get_unique_constraints(table):
            names.setdefault((table, "uq", tuple(unique["column_names"])), set()).add(unique["name"])
        for fk in inspector.get_foreign_keys(table):
            names[(table, "fk", tuple(fk["constrained_columns"]))] = fk["name"]
        for index in inspector.get_indexes(table):
            if index["name"].startswith("ix_"):
                names[(table, "ix", tuple(index["column_names"]))] = index["name"]
    return names


async def names_of(engine) -> dict:
    async with engine.connect() as conn:
        return await conn.run_sync(constraint_names)


async def create_all_names() -> dict:
    """Names ``create_all`` gives, which is what a fresh SQLite database gets."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return await names_of(engine)
    finally:
        await engine.dispose()


def only_names(names: dict) -> dict:
    return {key: (value if isinstance(value, str) or value is None else min(value)) for key, value in names.items()}


def naming_revision(alembic_cfg):
    return ScriptDirectory.from_config(alembic_cfg).get_revision(NAMING_REVISION).module


def run_in_context(sync_conn, fn):
    with Operations.context(MigrationContext.configure(sync_conn)):
        fn()


async def in_thread(fn, *args):
    with ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(executor, partial(fn, *args))


@pytest.fixture
async def legacy_engine(database_url, test_id, tmp_path, monkeypatch):
    """A database in the shape 0.12 leaves it: alembic chain up to the revision before naming, or its SQLite file."""
    if database_url.startswith("sqlite"):
        path = tmp_path / "legacy.db"
        with sqlite3.connect(path) as conn:
            conn.executescript(LEGACY_SQLITE_SCHEMA)
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        try:
            yield engine
        finally:
            await engine.dispose()
        return

    async with get_scoped_database_url(database_url, test_id) as scoped_url:
        engine = create_async_engine(scoped_url)
        try:
            alembic_cfg = create_alembic_config(engine.url.render_as_string(hide_password=False))
            # alembic builds its tables with the convention of the metadata: use the one of 0.12 to get its names
            monkeypatch.setattr(Base.metadata, "naming_convention", {"ix": "ix_%(column_0_label)s"})
            await in_thread(command.upgrade, alembic_cfg, PREVIOUS_REVISION)
            monkeypatch.undo()
            yield engine
        finally:
            await engine.dispose()


def test_metadata_has_a_naming_convention_for_every_kind_of_constraint():
    assert set(Base.metadata.naming_convention) >= {"ix", "uq", "ck", "fk", "pk"}


async def test_create_all_names_constraints_after_the_convention():
    names = only_names(await create_all_names())

    assert names[("trans_user_flags", "fk", ("user_id",))] == "fk_trans_user_flags_user_id_users"
    assert names[("trans_user_flags", "pk", ("id",))] == "pk_trans_user_flags"
    assert names[("trans_user_flags", "uq", ("user_id", "transaction_id", "type"))] == (
        "uq_trans_user_flags_user_id_transaction_id_type"
    )
    assert names[("trans_user_flags", "uq", ("id",))] == "uq_trans_user_flags_id"
    assert names[("messages", "ix", ("transaction_id",))] == "ix_messages_transaction_id"
    assert names[("transactions", "ix", ("endpoint",))] == "ix_transactions_endpoint"


async def assert_named_like_create_all(engine):
    expected = only_names(await create_all_names())
    actual = only_names(await names_of(engine))
    assert actual == {key: value for key, value in expected.items() if key in actual}
    # MySQL has no name for a primary key
    assert set(expected) - set(actual) <= {key for key in expected if key[1] == "pk"}


@parametrize_with_database_urls()
async def test_schema_reached_by_the_boot_path_is_named_like_create_all(sql_engine):
    # alembic chain on PostgreSQL and MySQL, create_all on SQLite
    await assert_named_like_create_all(sql_engine)


@parametrize_with_database_urls()
async def test_naming_migration_names_a_0_12_schema_like_create_all(legacy_engine):
    alembic_cfg = create_alembic_config(legacy_engine.url.render_as_string(hide_password=False))

    async with legacy_engine.begin() as conn:
        await conn.run_sync(run_in_context, naming_revision(alembic_cfg).upgrade)

    await assert_named_like_create_all(legacy_engine)


@parametrize_with_database_urls()
async def test_naming_migration_downgrade_restores_the_previous_names(legacy_engine):
    alembic_cfg = create_alembic_config(legacy_engine.url.render_as_string(hide_password=False))
    before = await names_of(legacy_engine)

    async with legacy_engine.begin() as conn:
        await conn.run_sync(run_in_context, naming_revision(alembic_cfg).upgrade)
    async with legacy_engine.begin() as conn:
        await conn.run_sync(run_in_context, naming_revision(alembic_cfg).downgrade)

    after = await names_of(legacy_engine)
    # the stacked duplicates are not recreated: one constraint of each kind remains
    duplicates = set() if legacy_engine.dialect.name == "sqlite" else STACKED_DUPLICATES
    assert {k: _without(v, duplicates) for k, v in after.items()} == {
        k: _without(v, duplicates) for k, v in before.items()
    }


def _without(value, duplicates):
    return value - duplicates if isinstance(value, set) else value


@parametrize_with_database_urls()
async def test_schema_is_current_after_migrating_from_0_12(legacy_engine):
    alembic_cfg = create_alembic_config(legacy_engine.url.render_as_string(hide_password=False))
    if legacy_engine.dialect.name == "sqlite":
        # SQLite is not migrated by alembic at boot: it is compared to the models
        async with legacy_engine.begin() as conn:
            await conn.run_sync(run_in_context, naming_revision(alembic_cfg).upgrade)
    else:
        await in_thread(command.upgrade, alembic_cfg, "head")

    await ensure_schema_is_current(legacy_engine)


def _insert_rows(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            INSERT INTO blobs (id, data, content_type) VALUES ('b1', x'00', 'text/plain');
            INSERT INTO users (id, username) VALUES (1, 'anonymous');
            INSERT INTO tags (id, name) VALUES (1, 'tag');
            INSERT INTO tag_values (id, tag_id, value) VALUES (1, 1, 'v');
            INSERT INTO transactions (id, type, endpoint, started_at) VALUES ('t1', 'http', 'e', '2026-01-01');
            INSERT INTO trans_tag_values (transaction_id, value_id) VALUES ('t1', 1);
            INSERT INTO trans_user_flags (id, type, user_id, transaction_id) VALUES (1, 1, 1, 't1');
            INSERT INTO messages (id, kind, summary, created_at, transaction_id)
                VALUES (1, 'request', 's', '2026-01-01', 't1');
            INSERT INTO metrics (id, name) VALUES (1, 'm');
            INSERT INTO metric_values (metric_id, created_at, value) VALUES (1, '2026-01-01', 3);
            """
        )


def _dump_rows(path):
    with sqlite3.connect(path) as conn:
        tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table' order by 1")]
        rows = {t: conn.execute(f"select * from {t} order by 1, 2").fetchall() for t in tables}
        rows.pop("alembic_version", None)
        return rows, conn.execute("PRAGMA foreign_key_check").fetchall()


@parametrize_with_database_urls("sqlite")
async def test_naming_migration_keeps_the_rows_of_a_sqlite_file(legacy_engine):
    """The alembic chain cannot run on SQLite (``ALTER COLUMN ... TYPE``), so the file is the 0.12 ``create_all`` one."""
    path = legacy_engine.url.database
    alembic_cfg = create_alembic_config(legacy_engine.url.render_as_string(hide_password=False))
    _insert_rows(path)
    before = _dump_rows(path)
    assert before[1] == []

    async with legacy_engine.begin() as conn:
        await conn.run_sync(run_in_context, naming_revision(alembic_cfg).upgrade)
    assert _dump_rows(path) == before

    async with legacy_engine.begin() as conn:
        await conn.run_sync(run_in_context, naming_revision(alembic_cfg).downgrade)
    assert _dump_rows(path) == before
