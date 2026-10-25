"""Basic users declared in the configuration become accounts once, never again (decision 21)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import (
    IMPORT_MARKER_USERNAME,
    MIGRATED,
    AccountKind,
    AccountsRepository,
    ReservedUsernameError,
)


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


async def migrated(accounts, username, **values):
    """An account as the migration leaves the ones that existed: disabled, waiting for the import."""
    await accounts.create(
        {"username": username, "role": Role.VIEWER, "disabled_at": datetime.now(UTC), "disabled_reason": MIGRATED}
        | values
    )


async def test_an_account_the_migration_disabled_is_enabled_and_made_admin(accounts):
    await migrated(accounts, "alice")

    await accounts.import_basic_users(["alice"])

    alice = await accounts.find_one({"username": "alice"})
    assert (alice.role, alice.disabled_at, alice.disabled_reason) == (Role.ADMIN, None, None)


async def test_a_decision_of_the_operator_before_the_first_start_wins(accounts):
    await migrated(accounts, "bob")
    await migrated(accounts, "mallory")
    await accounts.update_account("bob", role=Role.VIEWER)
    await accounts.update_account("mallory", disabled_at=datetime.now(UTC))

    await accounts.import_basic_users(["bob", "mallory"])

    bob = await accounts.find_one({"username": "bob"})
    mallory = await accounts.find_one({"username": "mallory"})
    assert (bob.role, bob.disabled_at is not None) == (Role.VIEWER, True)
    assert mallory.disabled_at is not None


async def test_an_account_the_operator_enabled_or_that_was_never_migrated_is_left_alone(accounts):
    await accounts.create({"username": "carol", "role": Role.EDITOR})
    await accounts.create({"username": "dave", "role": Role.VIEWER, "disabled_at": datetime.now(UTC)})

    await accounts.import_basic_users(["carol", "dave"])

    assert (await accounts.find_one({"username": "carol"})).role is Role.EDITOR
    assert (await accounts.find_one({"username": "dave"})).disabled_at is not None


async def test_a_disable_landing_during_the_import_is_not_lost(accounts, monkeypatch):
    await migrated(accounts, "alice")
    looked = accounts._import_done

    async def operator_disables_after_the_import_looked():
        done = await looked()
        await accounts.update_account("alice", disabled_at=datetime.now(UTC))
        return done

    monkeypatch.setattr(accounts, "_import_done", operator_disables_after_the_import_looked)

    await accounts.import_basic_users(["alice"])

    alice = await accounts.find_one({"username": "alice"})
    assert alice.disabled_at is not None and alice.role is Role.VIEWER


async def test_a_person_named_like_the_marker_does_not_make_the_import_skip_silently(accounts):
    await accounts.create({"username": IMPORT_MARKER_USERNAME})

    with pytest.raises(ReservedUsernameError):
        await accounts.import_basic_users(["alice"])

    assert await usernames(accounts) == [IMPORT_MARKER_USERNAME]
