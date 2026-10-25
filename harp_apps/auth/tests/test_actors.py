from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.actors import ActorResolver
from harp_apps.auth.models import AccountKind, AccountsRepository

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def accounts(sql_engine) -> AccountsRepository:
    return AccountsRepository(async_sessionmaker(sql_engine, expire_on_commit=False))


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def resolver(accounts, clock) -> ActorResolver:
    return ActorResolver(accounts, clock=clock)


async def test_actor_of_an_account_acts_with_the_role_of_the_account(resolver, accounts):
    await accounts.create({"username": "alice", "role": Role.EDITOR, "display_name": "Alice"})

    actor = await resolver.resolve("alice", via="basic")

    assert actor.role is Role.EDITOR
    assert (actor.account.username, actor.account.role, actor.account.display_name) == ("alice", Role.EDITOR, "Alice")
    assert actor.account.id is not None
    assert (actor.via, actor.via_id, actor.client) == ("basic", None, None)


async def test_actor_remembers_the_credential_and_the_client(resolver, accounts):
    await accounts.create({"username": "alice", "role": Role.ADMIN})

    actor = await resolver.resolve("alice", via="token", via_id="42", client="agent")

    assert (actor.via, actor.via_id, actor.client) == ("token", "42", "agent")


async def test_credential_cap_lowers_the_role_but_not_the_account(resolver, accounts):
    await accounts.create({"username": "alice", "role": Role.ADMIN})

    actor = await resolver.resolve("alice", via="token", cap=Role.VIEWER)

    assert actor.role is Role.VIEWER
    assert actor.account.role is Role.ADMIN


async def test_cap_never_raises_the_role(resolver, accounts):
    await accounts.create({"username": "alice", "role": Role.VIEWER})

    assert (await resolver.resolve("alice", via="token", cap=Role.ADMIN)).role is Role.VIEWER


async def test_role_is_read_from_the_account_on_every_request(resolver, accounts):
    account = await accounts.create({"username": "alice", "role": Role.ADMIN})
    assert (await resolver.resolve("alice", via="basic")).role is Role.ADMIN

    async with accounts.session_factory() as session:
        (await session.get(type(account), account.id)).role = Role.VIEWER
        await session.commit()

    assert (await resolver.resolve("alice", via="basic")).role is Role.VIEWER


async def test_disabled_account_resolves_to_nobody(resolver, accounts, clock):
    await accounts.create({"username": "alice", "role": Role.ADMIN, "disabled_at": clock.now})

    assert await resolver.resolve("alice", via="basic") is None


async def test_system_account_never_resolves(resolver, accounts):
    await accounts.create({"username": "anonymous", "kind": AccountKind.SYSTEM, "role": Role.ADMIN})

    assert await resolver.resolve("anonymous", via="basic") is None


async def test_unknown_account_resolves_to_nobody(resolver):
    assert await resolver.resolve("nobody", via="basic") is None


async def test_basic_user_declared_in_configuration_is_an_admin_even_before_its_account_exists(resolver, accounts):
    actor = await resolver.basic("carol")

    assert actor.role is Role.ADMIN
    account = await accounts.find_one({"username": "carol"})
    assert (account.kind, account.role) == (AccountKind.PERSON, Role.ADMIN)


async def test_basic_keeps_the_role_of_an_existing_account(resolver, accounts):
    await accounts.create({"username": "carol", "role": Role.VIEWER})

    assert (await resolver.basic("carol")).role is Role.VIEWER


async def test_basic_refuses_a_disabled_account(resolver, accounts, clock):
    await accounts.create({"username": "carol", "role": Role.ADMIN, "disabled_at": clock.now})

    assert await resolver.basic("carol") is None


async def last_seen(accounts, username):
    return (await accounts.find_one({"username": username})).last_seen_at


async def test_last_seen_is_written_on_the_first_request(resolver, accounts, clock):
    await accounts.create({"username": "alice", "role": Role.VIEWER})

    await resolver.resolve("alice", via="basic")

    assert await last_seen(accounts, "alice") == clock.now


async def test_last_seen_is_written_at_most_once_a_minute(resolver, accounts, clock):
    await accounts.create({"username": "alice", "role": Role.VIEWER})
    await resolver.resolve("alice", via="basic")

    clock.now += timedelta(seconds=59)
    await resolver.resolve("alice", via="basic")
    assert await last_seen(accounts, "alice") == NOW

    clock.now += timedelta(seconds=1)
    await resolver.resolve("alice", via="basic")
    assert await last_seen(accounts, "alice") == clock.now


async def test_last_seen_is_not_written_for_a_refused_account(resolver, accounts, clock):
    await accounts.create({"username": "alice", "role": Role.VIEWER, "disabled_at": clock.now})

    await resolver.resolve("alice", via="basic")

    assert await last_seen(accounts, "alice") is None
