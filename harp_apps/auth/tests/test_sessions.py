from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import AccountsRepository, IdentitiesRepository, Session, SessionsRepository
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.settings import AuthSettings

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.now = NOW

    def __call__(self):
        return self.now

    def advance(self, **delta):
        self.now += timedelta(**delta)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def sessions(factory, clock) -> SessionsService:
    return SessionsService(SessionsRepository(factory), AuthSettings(), clock=clock)


@pytest.fixture
async def alice(factory):
    account = await AccountsRepository(factory).create({"username": "alice", "role": Role.ADMIN})
    identity = await IdentitiesRepository(factory).create(
        {"account_id": account.id, "method": "password", "issuer": "", "subject": "alice"}
    )
    return account, identity


async def open_session(sessions, alice, **kwargs):
    account, identity = alice
    return await sessions.open(account.id, identity.id, **({"user_agent": "UA", "ip": "10.0.0.1"} | kwargs))


async def rows(factory):
    async with factory() as session:
        return list((await session.execute(select(Session).order_by(Session.id))).scalars())


async def test_an_opened_session_is_found_by_its_secret(sessions, alice):
    secret, opened = await open_session(sessions, alice)

    found = await sessions.authenticate(secret)

    assert found is not None and found.id == opened.id and found.account_id == alice[0].id


async def test_the_secret_is_not_stored(sessions, alice, factory):
    secret, _ = await open_session(sessions, alice)

    stored = (await rows(factory))[0]
    assert secret not in (stored.secret_hash, stored.user_agent, stored.ip)
    assert len(stored.secret_hash) == 64


async def test_two_sessions_have_unrelated_secrets(sessions, alice):
    (first, _), (second, _) = await open_session(sessions, alice), await open_session(sessions, alice)

    assert first != second and len(first) >= 43


async def test_the_session_records_where_it_came_from(sessions, alice, factory):
    await open_session(sessions, alice, user_agent="Firefox", ip="2001:db8::1")

    stored = (await rows(factory))[0]
    assert (stored.user_agent, stored.ip) == ("Firefox", "2001:db8::1")
    assert stored.expires_at == NOW + timedelta(days=7)


async def test_a_long_user_agent_is_cut_to_what_fits(sessions, alice, factory):
    await open_session(sessions, alice, user_agent="x" * 5000)

    assert len((await rows(factory))[0].user_agent) == 512


@pytest.mark.parametrize("secret", ["", "nope", "x" * 43, "x" * 5000, "../etc", "é" * 43])
async def test_an_unknown_secret_authenticates_nothing(sessions, alice, secret):
    await open_session(sessions, alice)

    assert await sessions.authenticate(secret) is None


async def test_a_session_ends_after_the_idle_timeout(sessions, alice, clock):
    secret, _ = await open_session(sessions, alice)

    clock.advance(hours=11, minutes=59)
    assert await sessions.authenticate(secret) is not None
    clock.advance(hours=12, minutes=1)
    assert await sessions.authenticate(secret) is None


async def test_activity_keeps_a_session_alive_until_the_maximum_age(sessions, alice, clock):
    secret, _ = await open_session(sessions, alice)

    for _ in range(13):  # a request every 11 hours, for almost 6 days
        clock.advance(hours=11)
        assert await sessions.authenticate(secret) is not None
    clock.advance(hours=11)  # 154 hours in
    assert await sessions.authenticate(secret) is not None
    clock.advance(hours=7)  # 161 hours in
    assert await sessions.authenticate(secret) is not None
    clock.advance(hours=8)  # past 168 hours (7 days), the session was active an instant ago
    assert await sessions.authenticate(secret) is None


async def test_the_limits_are_settings(factory, clock, alice):
    sessions = SessionsService(
        SessionsRepository(factory), AuthSettings(session_idle_hours=1, session_max_hours=2), clock=clock
    )
    secret, _ = await open_session(sessions, alice)

    clock.advance(minutes=61)

    assert await sessions.authenticate(secret) is None


async def test_last_seen_is_written_at_most_once_a_minute(sessions, alice, clock, factory):
    secret, _ = await open_session(sessions, alice)

    clock.advance(seconds=30)
    await sessions.authenticate(secret)
    assert (await rows(factory))[0].last_seen_at == NOW

    clock.advance(seconds=31)
    await sessions.authenticate(secret)
    assert (await rows(factory))[0].last_seen_at == clock.now


async def test_a_revoked_session_authenticates_nothing(sessions, alice):
    secret, opened = await open_session(sessions, alice)

    assert await sessions.revoke(opened.id) == 1

    assert await sessions.authenticate(secret) is None


async def test_revoking_twice_revokes_once(sessions, alice):
    _, opened = await open_session(sessions, alice)

    await sessions.revoke(opened.id)

    assert await sessions.revoke(opened.id) == 0


async def test_sign_out_everywhere_ends_every_session_of_the_account_and_no_other(sessions, alice, factory):
    other = await AccountsRepository(factory).create({"username": "bob"})
    other_identity = await IdentitiesRepository(factory).create(
        {"account_id": other.id, "method": "password", "issuer": "", "subject": "bob"}
    )
    first, _ = await open_session(sessions, alice)
    second, _ = await open_session(sessions, alice)
    bobs, _ = await sessions.open(other.id, other_identity.id, user_agent=None, ip=None)

    assert await sessions.revoke_all(alice[0].id) == 2

    assert await sessions.authenticate(first) is None
    assert await sessions.authenticate(second) is None
    assert await sessions.authenticate(bobs) is not None


async def test_ending_the_other_sessions_keeps_the_current_one(sessions, alice):
    current, opened = await open_session(sessions, alice)
    other, _ = await open_session(sessions, alice)

    assert await sessions.revoke_others(alice[0].id, keep=opened.id) == 1

    assert await sessions.authenticate(current) is not None
    assert await sessions.authenticate(other) is None
