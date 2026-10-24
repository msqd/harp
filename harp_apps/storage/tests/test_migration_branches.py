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
    ensure_schema_is_current,
    table_belongs_to,
)
from harp_apps.storage.utils.testing.sql import run_cli_migrate_command

STORAGE_HEAD = "c5e8b2d41f73"


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


async def test_database_migrated_before_branches_upgrades_cleanly(database_url, test_id):
    if database_url.startswith("sqlite"):
        pytest.skip("sqlite is not tracked by alembic")
    from harp_apps.storage.utils.testing.sql import get_scoped_database_url

    async with get_scoped_database_url(database_url, test_id) as url:
        cfg = create_alembic_config(url)
        # alembic_version holds a plain storage revision, as written before branch labels existed
        await _run(command.upgrade, cfg, "a1c7f3b52e04")
        result = await run_cli_migrate_command(url)

    assert result.exit_code == 0, result.output


def test_create_migration_refuses_an_unknown_application():
    from harp.commandline import migrations
    from harp.utils.testing.cli import CliRunner

    result = CliRunner().invoke(
        migrations.create_migration, ["nope", "msg", "--set", "storage.url=sqlite+aiosqlite:///:memory:"]
    )

    assert result.exit_code != 0
    assert "Unknown application 'nope'" in result.output
