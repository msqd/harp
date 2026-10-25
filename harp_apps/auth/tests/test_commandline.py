import asyncio
import sqlite3

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from harp.security.actor import Role
from harp.utils.testing.cli import CliRunner
from harp_apps.auth.commandline import create_account, disable_account, enable_account, set_role
from harp_apps.auth.models import AccountKind, AccountsRepository
from harp_apps.storage.models import Base


@pytest.fixture
def database(tmp_path):
    """A SQLite file as HARP leaves it once started: all tables there."""
    path = tmp_path / "harp.db"

    async def create():
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create())
    return path


def invoke(database, *args):
    return CliRunner().invoke(create_account, [*args, "--set", f"storage.url=sqlite+aiosqlite:///{database}"])


def accounts_of(database) -> list[tuple]:
    with sqlite3.connect(database) as conn:
        return conn.execute("SELECT username, kind, role, display_name, email FROM auth_accounts").fetchall()


def test_creates_an_account_with_the_given_role(database):
    result = invoke(database, "alice", "--role", "editor")

    assert result.exit_code == 0, result.output
    assert accounts_of(database) == [("alice", "person", "editor", None, None)]
    assert "alice" in result.output and "editor" in result.output


def test_creates_an_admin_to_recover_access(database):
    result = invoke(database, "rescue", "--role", "admin", "--display-name", "Rescue", "--email", "Rescue@Example.com")

    assert result.exit_code == 0, result.output
    assert accounts_of(database) == [("rescue", "person", "admin", "Rescue", "rescue@example.com")]


def test_the_role_is_mandatory(database):
    result = invoke(database, "alice")

    assert result.exit_code != 0
    assert "--role" in result.output
    assert accounts_of(database) == []


def test_an_unknown_role_is_refused(database):
    result = invoke(database, "alice", "--role", "root")

    assert result.exit_code != 0
    assert accounts_of(database) == []


def test_an_existing_account_is_left_as_it_is(database):
    assert invoke(database, "alice", "--role", "viewer").exit_code == 0

    result = invoke(database, "alice", "--role", "admin")

    assert result.exit_code != 0
    assert "alice" in result.output and "exists" in result.output
    assert accounts_of(database) == [("alice", "person", "viewer", None, None)]


def test_an_email_already_taken_is_refused(database):
    assert invoke(database, "alice", "--role", "viewer", "--email", "a@example.com").exit_code == 0

    result = invoke(database, "bob", "--role", "viewer", "--email", "A@example.com")

    assert result.exit_code != 0
    assert "email" in result.output
    assert [row[0] for row in accounts_of(database)] == ["alice"]


def test_a_database_without_the_schema_is_reported_not_crashed(tmp_path):
    sqlite3.connect(tmp_path / "empty.db").close()

    result = invoke(tmp_path / "empty.db", "alice", "--role", "admin")

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "outdated" in result.output


def test_the_command_is_part_of_the_harp_command():
    from harp.commandline import entrypoint

    assert entrypoint.commands["auth:create-account"] is create_account


def test_the_account_is_a_person(database):
    invoke(database, "alice", "--role", "admin")

    async def read():
        engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
        try:
            return await AccountsRepository(async_sessionmaker(engine)).find_one({"username": "alice"})
        finally:
            await engine.dispose()

    account = asyncio.run(read())
    assert (account.kind, account.role) == (AccountKind.PERSON, Role.ADMIN)


def run(database, command, *args):
    return CliRunner().invoke(command, [*args, "--set", f"storage.url=sqlite+aiosqlite:///{database}"])


def state_of(database, username):
    with sqlite3.connect(database) as conn:
        return conn.execute(
            "SELECT role, disabled_at IS NOT NULL FROM auth_accounts WHERE username = ?", (username,)
        ).fetchone()


def test_set_role_changes_the_role(database):
    invoke(database, "alice", "--role", "viewer")

    result = run(database, set_role, "alice", "admin")

    assert result.exit_code == 0, result.output
    assert state_of(database, "alice") == ("admin", 0)


def test_set_role_refuses_an_unknown_role_and_an_unknown_account(database):
    invoke(database, "alice", "--role", "viewer")

    assert run(database, set_role, "alice", "root").exit_code != 0
    result = run(database, set_role, "nobody", "admin")

    assert result.exit_code != 0
    assert "nobody" in result.output
    assert state_of(database, "alice") == ("viewer", 0)


def test_disable_then_enable_an_account_without_deleting_it(database):
    invoke(database, "alice", "--role", "admin")

    assert run(database, disable_account, "alice").exit_code == 0
    assert state_of(database, "alice") == ("admin", 1)

    assert run(database, enable_account, "alice").exit_code == 0
    assert state_of(database, "alice") == ("admin", 0)


def test_disabling_an_unknown_account_is_reported(database):
    result = run(database, disable_account, "nobody")

    assert result.exit_code != 0
    assert "nobody" in result.output


def test_a_system_account_cannot_be_changed(database):
    with sqlite3.connect(database) as conn:
        conn.execute("INSERT INTO auth_accounts (username, kind, role) VALUES ('anonymous', 'system', 'viewer')")

    assert run(database, set_role, "anonymous", "admin").exit_code != 0
    assert state_of(database, "anonymous") == ("viewer", 0)


def test_the_commands_are_part_of_the_harp_command():
    from harp.commandline import entrypoint

    for name, command in (
        ("auth:set-role", set_role),
        ("auth:disable-account", disable_account),
        ("auth:enable-account", enable_account),
    ):
        assert entrypoint.commands[name] is command


@pytest.mark.parametrize("username", ["basic-import", "anonymous"])
def test_reserved_system_names_cannot_be_created(database, username):
    result = invoke(database, username, "--role", "admin")

    assert result.exit_code != 0
    assert "reserved" in result.output
    assert accounts_of(database) == []


def test_disabling_and_enabling_leave_a_reason_the_import_does_not_touch(database):
    invoke(database, "alice", "--role", "viewer")

    run(database, disable_account, "alice")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT disabled_reason FROM auth_accounts").fetchone() == ("operator",)

    run(database, enable_account, "alice")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT disabled_reason FROM auth_accounts").fetchone() == (None,)
