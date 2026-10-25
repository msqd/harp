"""
The first revision of the auth branch takes ``users`` over as ``auth_accounts``.

Only PostgreSQL is migrated by alembic: SQLite gets ``create_all`` (an existing file is recreated on upgrade) and MySQL
is unsupported (ADR-0005, the revision logs a warning and does nothing there).
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.models import Base
from harp_apps.storage.utils.migrations import create_alembic_config, ensure_schema_is_current
from harp_apps.storage.utils.testing.sql import get_scoped_database_url

NAMING_REVISION = "e7a4d9c26b18"


async def in_thread(fn, *args):
    with ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(executor, partial(fn, *args))


@pytest.fixture
async def users_engine(database_url, test_id):
    """A PostgreSQL database in the shape the storage branch leaves it: a ``users`` table, favourites included."""
    async with get_scoped_database_url(database_url, test_id) as url:
        engine = create_async_engine(url)
        cfg = create_alembic_config(url)
        try:
            await in_thread(command.upgrade, cfg, "storage@head")
            async with engine.begin() as conn:
                await conn.execute(text("INSERT INTO users (username) VALUES ('alice'), ('anonymous')"))
                await conn.execute(text("INSERT INTO transactions (id, type, started_at) VALUES ('t1', 'http', now())"))
                await conn.execute(
                    text(
                        "INSERT INTO trans_user_flags (type, user_id, transaction_id) "
                        "SELECT 1, id, 't1' FROM users WHERE username = 'alice'"
                    )
                )
            yield engine
        finally:
            await engine.dispose()


def cfg_of(engine):
    return create_alembic_config(engine.url.render_as_string(hide_password=False))


async def upgrade(engine):
    await in_thread(command.upgrade, cfg_of(engine), "auth@head")


async def downgrade(engine):
    await in_thread(command.downgrade, cfg_of(engine), "auth@base")


async def rows(engine, query):
    async with engine.connect() as conn:
        return [tuple(row) for row in (await conn.execute(text(query))).fetchall()]


def test_first_revision_opens_the_auth_branch_after_the_naming_convention():
    script = ScriptDirectory.from_config(create_alembic_config("sqlite+aiosqlite:///:memory:"))
    first = script.get_revision("auth")

    assert first.down_revision is None
    assert first.branch_labels == {"auth"}
    assert first.dependencies == NAMING_REVISION


@parametrize_with_database_urls("postgresql")
async def test_users_become_auth_accounts(users_engine):
    await upgrade(users_engine)

    tables = await rows(
        users_engine, "SELECT table_name FROM information_schema.tables WHERE table_name IN ('users', 'auth_accounts')"
    )
    assert tables == [("auth_accounts",)]


@parametrize_with_database_urls("postgresql")
async def test_existing_accounts_become_dormant_viewers_and_anonymous_a_system_account(users_engine):
    """None gets access from the migration: the one-time import of the Basic users enables the ones configured."""
    await upgrade(users_engine)

    assert await rows(
        users_engine, "SELECT username, kind, role, disabled_at IS NOT NULL FROM auth_accounts ORDER BY username"
    ) == [
        ("alice", "person", "viewer", True),
        ("anonymous", "system", "viewer", False),
    ]
    assert await rows(users_engine, "SELECT username, disabled_reason FROM auth_accounts ORDER BY username") == [
        ("alice", "migrated"),
        ("anonymous", None),
    ]


@parametrize_with_database_urls("postgresql")
async def test_existing_accounts_get_a_creation_date_and_nothing_else_to_remember(users_engine):
    await upgrade(users_engine)

    assert (
        await rows(
            users_engine,
            "SELECT created_at IS NOT NULL, display_name, email, last_seen_at FROM auth_accounts",
        )
        == [(True, None, None, None)] * 2
    )


@parametrize_with_database_urls("postgresql")
async def test_favourites_keep_their_author(users_engine):
    await upgrade(users_engine)

    assert await rows(
        users_engine, "SELECT a.username FROM trans_user_flags f JOIN auth_accounts a ON a.id = f.user_id"
    ) == [("alice",)]


@parametrize_with_database_urls("postgresql")
async def test_new_accounts_may_have_a_username_of_255_characters(users_engine):
    await upgrade(users_engine)

    async with users_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO auth_accounts (username, kind, role) VALUES (:u, 'person', 'viewer')"), {"u": "x" * 255}
        )


@parametrize_with_database_urls("postgresql")
async def test_email_is_unique_and_lower_cased_by_the_database(users_engine):
    await upgrade(users_engine)

    insert = text("INSERT INTO auth_accounts (username, kind, role, email) VALUES (:u, 'person', 'viewer', :e)")
    async with users_engine.begin() as conn:
        await conn.execute(insert, {"u": "bob", "e": "bob@example.com"})
    for username, email in (("bob2", "bob@example.com"), ("bob3", "BOB@example.com")):
        with pytest.raises(Exception, match="auth_accounts"):
            async with users_engine.begin() as conn:
                await conn.execute(insert, {"u": username, "e": email})


@parametrize_with_database_urls("postgresql")
async def test_migrated_schema_is_the_one_of_the_models(users_engine, database_url, test_id):
    await upgrade(users_engine)
    await ensure_schema_is_current(users_engine, alembic_cfg=cfg_of(users_engine))

    async with get_scoped_database_url(database_url, f"{test_id}_models") as url:
        reference = create_async_engine(url)
        try:
            async with reference.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with reference.connect() as conn:
                expected = await conn.run_sync(_schema)
        finally:
            await reference.dispose()

    async with users_engine.connect() as conn:
        assert await conn.run_sync(_schema) == expected


def _schema(sync_conn):
    """Columns, constraint names and indexes of the tables the take over touches."""
    inspector = inspect(sync_conn)
    schema = {}
    for table in ("auth_accounts", "trans_user_flags", "auth_identities", "auth_sessions", "auth_invitations"):
        schema[table] = {
            "columns": {
                c["name"]: (str(c["type"]), c["nullable"], c["default"] is not None)
                for c in inspector.get_columns(table)
            },
            "pk": inspector.get_pk_constraint(table)["name"],
            # the history stacked a unique on every id, a primary key already; create_all on PostgreSQL does not
            "uniques": {
                u["name"]: tuple(u["column_names"])
                for u in inspector.get_unique_constraints(table)
                if u["column_names"] != ["id"]
            },
            "foreign keys": {
                fk["name"]: (fk["referred_table"], fk["options"].get("ondelete"))
                for fk in inspector.get_foreign_keys(table)
            },
            "checks": {c["name"]: c["sqltext"] for c in inspector.get_check_constraints(table)},
            "indexes": {i["name"]: tuple(i["column_names"]) for i in inspector.get_indexes(table)}
            if table.startswith(("auth_identities", "auth_sessions", "auth_invitations"))
            else {},
        }
    return schema


@parametrize_with_database_urls("postgresql")
async def test_downgrade_restores_users_and_their_favourites(users_engine):
    await upgrade(users_engine)
    await downgrade(users_engine)

    assert await rows(users_engine, "SELECT username FROM users ORDER BY username") == [("alice",), ("anonymous",)]
    assert await rows(users_engine, "SELECT u.username FROM trans_user_flags f JOIN users u ON u.id = f.user_id") == [
        ("alice",)
    ]
    columns = await rows(
        users_engine, "SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY 1"
    )
    assert columns == [("id",), ("username",)]
    assert (
        await rows(users_engine, "SELECT table_name FROM information_schema.tables WHERE table_name = 'auth_accounts'")
        == []
    )


@parametrize_with_database_urls("postgresql")
async def test_downgrade_then_upgrade_again(users_engine):
    await upgrade(users_engine)
    await downgrade(users_engine)
    await upgrade(users_engine)

    assert await rows(users_engine, "SELECT username, role FROM auth_accounts ORDER BY username") == [
        ("alice", "viewer"),
        ("anonymous", "viewer"),
    ]
