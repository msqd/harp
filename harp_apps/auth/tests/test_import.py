"""Basic users declared in the configuration become accounts once, never again (decision 21)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import IMPORT_MARKER_USERNAME, Account, AccountKind, AccountsRepository


@pytest.fixture
def accounts(sql_engine) -> AccountsRepository:
    return AccountsRepository(async_sessionmaker(sql_engine, expire_on_commit=False))


async def usernames(accounts, kind=AccountKind.PERSON):
    return sorted(a.username for a in await accounts.find_all() if a.kind == kind)


async def test_configured_users_become_enabled_admin_people(accounts):
    assert await accounts.import_basic_users(["alice", "bob"]) is True

    alice = await accounts.find_one({"username": "alice"})
    assert (alice.kind, alice.role, alice.disabled_at) == (AccountKind.PERSON, Role.ADMIN, None)
    assert await usernames(accounts) == ["alice", "bob"]


async def test_an_account_that_exists_is_enabled_and_made_admin(accounts):
    await accounts.create({"username": "alice", "role": Role.VIEWER, "disabled_at": datetime.now(UTC)})

    await accounts.import_basic_users(["alice"])

    alice = await accounts.find_one({"username": "alice"})
    assert (alice.role, alice.disabled_at) == (Role.ADMIN, None)


async def test_the_import_runs_once(accounts):
    await accounts.import_basic_users(["alice"])

    assert await accounts.import_basic_users(["alice", "bob"]) is False
    assert await usernames(accounts) == ["alice"]


async def test_a_deleted_account_is_not_recreated_by_a_later_import(accounts):
    await accounts.import_basic_users(["alice"])
    alice = await accounts.find_one({"username": "alice"})
    async with accounts.session_factory() as session:
        await session.delete(await session.get(Account, alice.id))
        await session.commit()

    await accounts.import_basic_users(["alice"])

    assert await usernames(accounts) == []


async def test_a_later_import_leaves_roles_and_disabling_alone(accounts):
    await accounts.import_basic_users(["alice"])
    async with accounts.session_factory() as session:
        await session.execute(update(Account).values(role=Role.VIEWER, disabled_at=datetime.now(UTC)))
        await session.commit()

    await accounts.import_basic_users(["alice"])

    alice = await accounts.find_one({"username": "alice"})
    assert alice.role is Role.VIEWER and alice.disabled_at is not None


async def test_the_import_is_recorded_by_a_system_account_that_cannot_sign_in(accounts):
    await accounts.import_basic_users([])

    marker = await accounts.find_one({"username": IMPORT_MARKER_USERNAME})
    assert marker.kind is AccountKind.SYSTEM


async def test_system_accounts_are_not_imported(accounts):
    await accounts.create({"username": "anonymous", "kind": AccountKind.SYSTEM, "role": Role.VIEWER})

    await accounts.import_basic_users(["anonymous"])

    anonymous = await accounts.find_one({"username": "anonymous"})
    assert (anonymous.kind, anonymous.role) == (AccountKind.SYSTEM, Role.VIEWER)
