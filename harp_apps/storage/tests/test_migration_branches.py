import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, Table, text
from sqlalchemy.ext.asyncio import create_async_engine

from harp_apps.storage.models import Base
from harp_apps.storage.utils.migrations import (
    create_alembic_config,
    create_revision,
    current_revisions_by_application,
    discover_migration_locations,
    UnknownRevisionError,
    check_prefixes,
    ensure_schema_is_current,
    table_belongs_to,
)
from harp_apps.storage.utils.testing.sql import run_cli_migrate_command

STORAGE_HEAD = "e7a4d9c26b18"


def _write_revision(versions: Path, *, revision, label, down_revision=None):
    versions.mkdir(parents=True, exist_ok=True)
    (versions / f"{revision}.py").write_text(
        f"revision = {revision!r}\n"
        f"down_revision = {down_revision!r}\n"
        f"branch_labels = {(label,) if label else None!r}\n"
        "depends_on = None\n\n\n"
        "def upgrade():\n    pass\n\n\n"
        "def downgrade():\n    pass\n"
    )


def _application_tree(root: Path, *, with_migrations, without_migrations=()):
    for name in with_migrations:
        _write_revision(root / name / "migrations" / "versions", revision=f"{name}0001", label=name)
    for name in without_migrations:
        (root / name).mkdir()
    return root


def test_discovery_lists_every_application_with_a_versions_folder(tmp_path):
    root = _application_tree(tmp_path, with_migrations=["auth", "storage"], without_migrations=["proxy"])
    (root / "dashboard" / "migrations").mkdir(parents=True)  # a migrations folder without versions

    assert discover_migration_locations(root) == {
        "auth": root / "auth" / "migrations" / "versions",
        "storage": root / "storage" / "migrations" / "versions",
    }


def test_discovery_finds_storage_in_the_package():
    assert "storage" in discover_migration_locations()


def test_storage_revisions_form_the_storage_branch():
    script = ScriptDirectory.from_config(create_alembic_config("sqlite+aiosqlite:///:memory:"))

    assert script.get_heads() == [STORAGE_HEAD]
    assert script.get_revision("storage@head").revision == STORAGE_HEAD
    assert script.get_revision("storage").revision == "248285939c4c"


def test_config_lists_every_discovered_application_whatever_the_settings(tmp_path):
    root = _application_tree(tmp_path, with_migrations=["auth", "storage"])
    locations = discover_migration_locations(root)

    script = ScriptDirectory.from_config(create_alembic_config("sqlite+aiosqlite:///:memory:", locations=locations))

    assert sorted(script.get_heads()) == ["auth0001", "storage0001"]


def test_storage_owns_what_no_other_application_claims():
    applications = ["auth", "http_cache", "storage"]

    assert table_belongs_to("storage", "transactions", applications)
    assert table_belongs_to("storage", "blobs", applications)
    assert not table_belongs_to("storage", "auth_users", applications)
    assert not table_belongs_to("storage", "http_cache_entries", applications)
    assert table_belongs_to("auth", "auth_users", applications)
    assert not table_belongs_to("auth", "transactions", applications)
    assert not table_belongs_to("auth", "http_cache_entries", applications)


def test_storage_tables_are_all_storage_owned():
    for table in Base.metadata.sorted_tables:
        assert table_belongs_to("storage", table.name, ["auth", "storage"])


async def _run(func, *args):
    with ThreadPoolExecutor() as executor:
        return await asyncio.get_event_loop().run_in_executor(executor, partial(func, *args))


def _revision_text(path: Path) -> str:
    (file,) = list(path.glob("*.py"))
    return file.read_text()


@pytest.fixture
def extra_table():
    table = Table("auth_branch_test_things", Base.metadata, Column("id", Integer, primary_key=True))
    try:
        yield table
    finally:
        Base.metadata.remove(table)


async def test_a_model_change_in_one_application_stays_out_of_another_revision(tmp_path, extra_table):
    db = tmp_path / "autogen.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        # a database holding storage's tables, and nothing of auth's
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("DROP TABLE auth_branch_test_things"))
    await engine.dispose()

    locations = {"storage": tmp_path / "storage_versions", "auth": tmp_path / "auth_versions"}
    for path in locations.values():
        path.mkdir()
    cfg = create_alembic_config(f"sqlite+aiosqlite:///{db}", locations=locations)

    await _run(create_revision, cfg, "storage", "storage only")
    await _run(command.upgrade, cfg, "heads")
    await _run(create_revision, cfg, "auth", "auth only")

    storage_revision = _revision_text(locations["storage"])
    auth_revision = _revision_text(locations["auth"])
    assert "auth_branch_test_things" not in storage_revision
    assert "create_table('auth_branch_test_things'" in auth_revision.replace('"', "'")
    assert "transactions" not in auth_revision  # storage tables are not auth tables


async def test_first_revision_of_an_application_opens_its_branch(tmp_path):
    db = tmp_path / "branch.db"
    storage_versions = discover_migration_locations()["storage"]
    locations = {"storage": storage_versions, "auth": tmp_path / "auth_versions"}
    locations["auth"].mkdir()
    cfg = create_alembic_config(f"sqlite+aiosqlite:///{db}", locations=locations)
    await _run(command.stamp, cfg, "heads")

    await _run(create_revision, cfg, "auth", "first")

    script = ScriptDirectory.from_config(cfg)
    assert script.get_revision("auth").down_revision is None
    assert STORAGE_HEAD in script.get_heads()
    assert len(script.get_heads()) == 2
    assert script.get_revision("storage@head").revision == STORAGE_HEAD


async def test_boots_when_the_database_holds_the_head_of_an_application_not_enabled(tmp_path):
    root = _application_tree(tmp_path, with_migrations=["auth"])
    locations = {"storage": discover_migration_locations()["storage"], **discover_migration_locations(root)}
    # the database was migrated while auth was enabled; auth is no longer enabled, its folder is still listed
    db = tmp_path / "boot.db"
    cfg = create_alembic_config(f"sqlite+aiosqlite:///{db}", locations=locations)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run(command.stamp, cfg, "storage@head")
    await _run(command.upgrade, cfg, "heads")

    async with engine.connect() as conn:
        current = await conn.run_sync(lambda c: current_revisions_by_application(c, cfg))
    await engine.dispose()

    assert current == {"auth": "auth0001", "storage": STORAGE_HEAD}


async def test_ensure_schema_is_current_checks_every_head(tmp_path, sql_engine):
    if sql_engine.dialect.name == "sqlite":
        pytest.skip("sqlite schema is checked against the models, not alembic")

    root = _application_tree(tmp_path, with_migrations=["auth"])
    locations = {"storage": discover_migration_locations()["storage"], **discover_migration_locations(root)}
    cfg = create_alembic_config(sql_engine.url.render_as_string(hide_password=False), locations=locations)

    # storage is at its head, auth has a branch that was never applied
    from harp.errors import OutdatedSchemaError

    with pytest.raises(OutdatedSchemaError, match="auth0001"):
        await ensure_schema_is_current(sql_engine, alembic_cfg=cfg)

    await _run(command.upgrade, cfg, "heads")
    await ensure_schema_is_current(sql_engine, alembic_cfg=cfg)


async def test_migrate_status_shows_current_revision_per_application(database_url, test_id):
    if database_url.startswith("sqlite"):
        pytest.skip("sqlite is not tracked by alembic")
    from harp_apps.storage.utils.testing.sql import get_scoped_database_url

    async with get_scoped_database_url(database_url, test_id) as url:
        up = await run_cli_migrate_command(url)
        assert up.exit_code == 0, up.output

        status = await run_cli_migrate_command(url, operation="status", revision=None)

    assert status.exit_code == 0, status.output
    assert f"storage: {STORAGE_HEAD}" in status.output


async def test_database_migrated_before_branches_upgrades_all_heads(database_url, test_id, tmp_path):
    if database_url.startswith("sqlite"):
        pytest.skip("sqlite is not tracked by alembic")
    from harp_apps.storage.utils.testing.sql import get_scoped_database_url

    root = _application_tree(tmp_path, with_migrations=["auth"])
    locations = {"storage": discover_migration_locations()["storage"], **discover_migration_locations(root)}

    async with get_scoped_database_url(database_url, test_id) as url:
        cfg = create_alembic_config(url, locations=locations)
        # a database as 0.12 left it: only storage, a plain revision in alembic_version
        await _run(command.upgrade, cfg, "storage@a1c7f3b52e04")
        await _run(command.upgrade, cfg, "heads")
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            current = await conn.run_sync(lambda c: current_revisions_by_application(c, cfg))
        await engine.dispose()

    assert current == {"auth": "auth0001", "storage": STORAGE_HEAD}


async def test_migrate_status_is_readable_when_the_database_holds_an_unknown_revision(database_url, test_id):
    if database_url.startswith("sqlite"):
        pytest.skip("sqlite is not tracked by alembic")
    from harp_apps.storage.utils.testing.sql import get_scoped_database_url

    async with get_scoped_database_url(database_url, test_id) as url:
        assert (await run_cli_migrate_command(url)).exit_code == 0
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE alembic_version SET version_num = 'deadbeef0000'"))
        await engine.dispose()

        status = await run_cli_migrate_command(url, operation="status", revision=None)

    assert status.exit_code != 0
    assert "deadbeef0000" in status.output
    assert "Traceback" not in status.output


def test_unknown_revision_in_the_database_is_reported(tmp_path):
    import sqlite3

    db = tmp_path / "unknown.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conn.execute("INSERT INTO alembic_version VALUES ('deadbeef0000')")
    from sqlalchemy import create_engine

    cfg = create_alembic_config(f"sqlite+aiosqlite:///{db}")
    with create_engine(f"sqlite:///{db}").connect() as conn:
        with pytest.raises(UnknownRevisionError, match="deadbeef0000"):
            current_revisions_by_application(conn, cfg)


def test_longest_prefix_wins_when_prefixes_overlap():
    applications = ["cache", "cache_index", "storage"]

    assert table_belongs_to("cache_index", "cache_index_entries", applications)
    assert not table_belongs_to("cache", "cache_index_entries", applications)
    assert table_belongs_to("cache", "cache_entries", applications)


def test_a_model_without_its_application_prefix_is_refused():
    tables = [("harp_apps.auth.models", "auth_users"), ("harp_apps.auth.models", "sessions")]

    with pytest.raises(ValueError, match="sessions"):
        check_prefixes("auth", tables, ["auth", "storage"])


def test_other_applications_models_are_not_checked_against_this_one():
    tables = [("harp_apps.storage.models", "transactions"), ("harp_apps.auth.models", "auth_users")]

    check_prefixes("auth", tables, ["auth", "storage"])
    check_prefixes("storage", [("harp_apps.storage.models", "transactions")], ["auth", "storage"])


def test_create_revision_refuses_an_unprefixed_table(monkeypatch, tmp_path):
    from harp_apps.storage.utils import migrations

    monkeypatch.setattr(migrations, "model_tables", lambda: [("harp_apps.auth.models", "sessions")])
    auth = tmp_path / "auth_versions"
    auth.mkdir()
    cfg = create_alembic_config("sqlite+aiosqlite:///:memory:", locations={"auth": auth})

    with pytest.raises(ValueError, match="sessions"):
        create_revision(cfg, "auth", "msg")
    assert not list(auth.glob("*.py"))


def test_create_migration_command_writes_the_application_revision(tmp_path, monkeypatch, extra_table):
    import sqlite3

    from harp.commandline import migrations
    from harp.utils.testing.cli import CliRunner
    from harp_apps.storage.utils import migrations as utils

    locations = {"storage": tmp_path / "storage_versions", "auth": tmp_path / "auth_versions"}
    for path in locations.values():
        path.mkdir()
    monkeypatch.setattr(utils, "discover_migration_locations", lambda root=None: locations)
    db = tmp_path / "cli.db"
    sqlite3.connect(db).close()

    result = CliRunner().invoke(
        migrations.create_migration, ["auth", "add things", "--set", f"storage.url=sqlite+aiosqlite:///{db}"]
    )

    assert result.exit_code == 0, result.output
    assert "auth_branch_test_things" in _revision_text(locations["auth"])
    assert not list(locations["storage"].glob("*.py"))


def test_create_migration_refuses_an_unknown_application():
    from harp.commandline import migrations
    from harp.utils.testing.cli import CliRunner

    result = CliRunner().invoke(
        migrations.create_migration, ["nope", "msg", "--set", "storage.url=sqlite+aiosqlite:///:memory:"]
    )

    assert result.exit_code != 0
    assert "Unknown application 'nope'" in result.output
