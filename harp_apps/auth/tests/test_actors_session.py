from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.actors import ActorResolver
from harp_apps.auth.models import AccountsRepository, IdentitiesRepository, SessionsRepository
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.settings import AuthSettings

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def sessions(factory):
    return SessionsService(SessionsRepository(factory), AuthSettings(), clock=lambda: NOW)


@pytest.fixture
def resolver(factory, sessions):
    return ActorResolver(AccountsRepository(factory), sessions=sessions, clock=lambda: NOW)


@pytest.fixture
async def alice(factory):
    accounts = AccountsRepository(factory)
    account = await accounts.create({"username": "alice", "role": Role.EDITOR, "display_name": "Alice"})
    identity = await IdentitiesRepository(factory).create(
        {"account_id": account.id, "method": "password", "issuer": "", "subject": "alice"}
    )
    return account, identity


async def test_a_session_resolves_to_the_actor_of_its_account(resolver, sessions, alice):
    secret, row = await sessions.open(alice[0].id, alice[1].id, user_agent=None, ip=None)

    actor = await resolver.session(secret)

    assert (actor.account.username, actor.role, actor.via, actor.via_id) == (
        "alice",
        Role.EDITOR,
        "session",
        str(row.id),
    )


async def test_the_role_is_the_one_of_the_account_at_this_request(resolver, sessions, alice, factory):
    secret, _ = await sessions.open(alice[0].id, alice[1].id, user_agent=None, ip=None)
    await AccountsRepository(factory).update_account("alice", role=Role.VIEWER)

    assert (await resolver.session(secret)).role is Role.VIEWER


async def test_disabling_the_account_ends_its_sessions_at_the_next_request(resolver, sessions, alice, factory):
    secret, _ = await sessions.open(alice[0].id, alice[1].id, user_agent=None, ip=None)
    await AccountsRepository(factory).update_account("alice", disabled_at=NOW)

    assert await resolver.session(secret) is None


async def test_an_unknown_or_revoked_session_resolves_to_nobody(resolver, sessions, alice):
    secret, row = await sessions.open(alice[0].id, alice[1].id, user_agent=None, ip=None)
    await sessions.revoke(row.id)

    assert await resolver.session(secret) is None
    assert await resolver.session("x" * 43) is None
    assert await resolver.session("") is None


async def test_a_resolver_without_sessions_resolves_none(factory):
    resolver = ActorResolver(AccountsRepository(factory))

    assert await resolver.session("x" * 43) is None
