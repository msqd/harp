from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
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
async def alice(factory):
    account = await AccountsRepository(factory).create({"username": "alice", "role": Role.EDITOR})
    identity = await IdentitiesRepository(factory).create(
        {"account_id": account.id, "method": "password", "issuer": "", "subject": "alice", "password_hash": "h"}
    )
    return account, identity


async def test_a_session_opened_with_a_version_the_identity_has_gone_past_is_void(factory, sessions, alice):
    account, identity = alice
    secret, _ = await sessions.open(account.id, identity.id, user_agent=None, ip=None, credential_version=0)
    stale, _ = await sessions.open(account.id, identity.id, user_agent=None, ip=None, credential_version=0)
    kept_secret, kept = await sessions.open(account.id, identity.id, user_agent=None, ip=None, credential_version=0)

    await IdentitiesRepository(factory).replace_password(
        identity.id, "new", account_id=account.id, keep=kept.id, at=NOW
    )

    assert await sessions.authenticate(kept_secret) is not None
    assert await sessions.authenticate(secret) is None
    assert await sessions.authenticate(stale) is None


async def test_the_version_alone_voids_a_session_that_was_not_revoked(factory, sessions, alice):
    from sqlalchemy import update

    from harp_apps.auth.models import Identity

    account, identity = alice
    secret, _ = await sessions.open(account.id, identity.id, user_agent=None, ip=None, credential_version=0)
    async with factory() as db:
        await db.execute(update(Identity).where(Identity.id == identity.id).values(password_version=1))
        await db.commit()

    assert await sessions.authenticate(secret) is None


async def test_a_session_opened_after_the_change_with_the_new_version_works(factory, sessions, alice):
    account, identity = alice
    await IdentitiesRepository(factory).replace_password(identity.id, "new", account_id=account.id, keep=0, at=NOW)
    current, _ = await IdentitiesRepository(factory).find_password("alice")

    secret, _ = await sessions.open(
        account.id, identity.id, user_agent=None, ip=None, credential_version=current.password_version
    )

    assert await sessions.authenticate(secret) is not None
