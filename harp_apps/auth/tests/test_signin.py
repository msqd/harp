from datetime import UTC, datetime

import pytest
from argon2 import PasswordHasher as Argon2
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import AccountsRepository, IdentitiesRepository, SessionsRepository
from harp_apps.auth.passwords import PasswordHasher, PasswordPolicyError
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.settings import AuthSettings
from harp_apps.auth.signin import Authenticator, Refused, Signed, Throttled
from harp_apps.auth.throttle import FREE_FAILURES, SignInThrottle

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class Clock:
    now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def hasher():
    return PasswordHasher()


@pytest.fixture
def throttle():
    return SignInThrottle()


@pytest.fixture
def identities(factory):
    return IdentitiesRepository(factory)


@pytest.fixture
def sessions(factory, clock):
    return SessionsService(SessionsRepository(factory), AuthSettings(), clock=clock)


@pytest.fixture
def authenticator(identities, sessions, hasher, throttle, clock):
    return Authenticator(identities, sessions, hasher, throttle, clock=clock)


@pytest.fixture
async def alice(factory, identities, hasher):
    account = await AccountsRepository(factory).create({"username": "alice", "role": Role.EDITOR})
    await identities.create(
        {
            "account_id": account.id,
            "method": "password",
            "issuer": "",
            "subject": "alice",
            "password_hash": await hasher.hash(PASSWORD),
        }
    )
    return account


async def sign_in(authenticator, username="alice", password=PASSWORD, ip="10.0.0.1"):
    return await authenticator.sign_in(username, password, ip=ip, user_agent="UA")


async def test_the_right_password_opens_a_session(authenticator, alice, sessions):
    result = await sign_in(authenticator)

    assert isinstance(result, Signed)
    assert (await sessions.authenticate(result.secret)).account_id == alice.id


async def test_signing_in_records_the_time_on_the_identity(authenticator, alice, identities, clock):
    await sign_in(authenticator)

    identity, _ = await identities.find_password("alice")
    assert identity.last_sign_in_at == clock.now


@pytest.mark.parametrize("username, password", [("alice", "wrong password, quite long"), ("nobody", PASSWORD)])
async def test_a_wrong_password_and_an_unknown_account_are_refused_the_same_way(
    authenticator, alice, username, password
):
    assert await sign_in(authenticator, username, password) == Refused()


async def test_an_unknown_account_pays_the_verification_of_a_wrong_password(authenticator, alice, hasher, monkeypatch):
    verified = []
    original = hasher._verify_sync
    monkeypatch.setattr(hasher, "_verify_sync", lambda p, s: verified.append(s) or original(p, s))

    await sign_in(authenticator, "alice", "wrong password, quite long")
    await sign_in(authenticator, "nobody", "wrong password, quite long")

    assert len(verified) == 2 and all(h.startswith("$argon2id$") for h in verified)


async def test_a_disabled_account_is_refused_with_the_right_password_after_a_verification(
    authenticator, alice, factory, hasher, monkeypatch
):
    await AccountsRepository(factory).update_account("alice", disabled_at=NOW)
    verified = []
    original = hasher._verify_sync
    monkeypatch.setattr(hasher, "_verify_sync", lambda p, s: verified.append(s) or original(p, s))

    assert await sign_in(authenticator) == Refused()
    assert len(verified) == 1


async def test_an_account_without_a_password_is_refused(authenticator, factory, identities):
    account = await AccountsRepository(factory).create({"username": "oidc-only"})
    await identities.create(
        {"account_id": account.id, "method": "oidc", "issuer": "https://idp.example", "subject": "oidc-only"}
    )

    assert await sign_in(authenticator, "oidc-only", PASSWORD) == Refused()


@pytest.mark.parametrize("username, password", [("", PASSWORD), ("alice", ""), ("alice", "x" * 5000), ("a" * 300, "x")])
async def test_absurd_input_is_refused_without_looking_anything_up(authenticator, alice, username, password):
    assert await sign_in(authenticator, username, password) == Refused()


async def test_failures_slow_the_account_down_and_the_right_password_waits_too(authenticator, alice):
    for _ in range(FREE_FAILURES):
        assert await sign_in(authenticator, password="wrong password, quite long") == Refused()

    result = await sign_in(authenticator)

    assert isinstance(result, Throttled) and result.retry_after > 0


async def test_guesses_sent_at_once_meet_the_wait_as_the_others_do(authenticator, alice, hasher, monkeypatch):
    import asyncio

    verified = []
    original = hasher._verify_sync
    monkeypatch.setattr(hasher, "_verify_sync", lambda p, s: verified.append(s) or original(p, s))

    results = await asyncio.gather(
        *(sign_in(authenticator, password=f"wrong guess number {i}") for i in range(40)),
    )

    assert len(verified) <= FREE_FAILURES
    assert sum(isinstance(r, Throttled) for r in results) >= 40 - FREE_FAILURES


async def test_concurrent_sign_ins_of_the_right_password_are_not_throttled(authenticator, alice):
    import asyncio

    results = await asyncio.gather(*(sign_in(authenticator) for _ in range(FREE_FAILURES)))

    assert all(isinstance(r, Signed) for r in results)


async def test_a_wait_is_not_a_lockout(authenticator, alice, throttle):
    for _ in range(FREE_FAILURES):
        await sign_in(authenticator, password="wrong password, quite long")
    throttle.clock = lambda: 10**9  # much later

    assert isinstance(await sign_in(authenticator), Signed)


async def test_a_throttled_attempt_does_not_make_the_wait_longer(authenticator, alice, throttle):
    for _ in range(FREE_FAILURES):
        await sign_in(authenticator, password="wrong password, quite long")
    before = throttle.retry_after("alice", "10.0.0.1")

    for _ in range(5):
        await sign_in(authenticator, password="wrong password, quite long")

    assert throttle.retry_after("alice", "10.0.0.1") <= before


async def test_a_success_clears_the_failures_of_the_account(authenticator, alice, throttle):
    for _ in range(FREE_FAILURES - 1):
        await sign_in(authenticator, password="wrong password, quite long")

    await sign_in(authenticator)

    assert throttle.retry_after("alice", "10.0.0.9") == 0


async def test_a_password_hashed_with_old_parameters_is_hashed_again(authenticator, factory, identities):
    account = await AccountsRepository(factory).create({"username": "bob"})
    weak = Argon2(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)
    await identities.create(
        {"account_id": account.id, "method": "password", "issuer": "", "subject": "bob", "password_hash": weak}
    )

    assert isinstance(await sign_in(authenticator, "bob"), Signed)

    identity, _ = await identities.find_password("bob")
    assert identity.password_hash != weak and identity.password_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert isinstance(await sign_in(authenticator, "bob"), Signed)


async def test_changing_the_password_replaces_it_and_ends_the_other_sessions(authenticator, alice, sessions):
    keep = await sign_in(authenticator)
    other = await sign_in(authenticator)
    new_password = "another very long passphrase"

    assert await authenticator.change_password(alice.id, "alice", PASSWORD, new_password, keep=keep.session.id, ip="x")

    assert await sessions.authenticate(keep.secret) is not None
    assert await sessions.authenticate(other.secret) is None
    assert await sign_in(authenticator, password=PASSWORD) == Refused()
    assert isinstance(await sign_in(authenticator, password=new_password), Signed)


async def test_changing_the_password_needs_the_current_one(authenticator, alice):
    keep = await sign_in(authenticator)

    changed = await authenticator.change_password(
        alice.id, "alice", "not the current one, no", "another very long passphrase", keep=keep.session.id, ip="x"
    )

    assert changed is False
    assert isinstance(await sign_in(authenticator), Signed)


async def test_the_new_password_must_meet_the_policy(authenticator, alice):
    keep = await sign_in(authenticator)

    with pytest.raises(PasswordPolicyError):
        await authenticator.change_password(alice.id, "alice", PASSWORD, "short", keep=keep.session.id, ip="x")

    assert isinstance(await sign_in(authenticator), Signed)


async def test_guessing_the_current_password_is_throttled_like_a_sign_in(authenticator, alice):
    keep = await sign_in(authenticator)
    for _ in range(FREE_FAILURES):
        await authenticator.change_password(
            alice.id, "alice", "not the current one, no", "another very long passphrase", keep=keep.session.id, ip="x"
        )

    result = await authenticator.change_password(
        alice.id, "alice", PASSWORD, "another very long passphrase", keep=keep.session.id, ip="x"
    )

    assert result is False
