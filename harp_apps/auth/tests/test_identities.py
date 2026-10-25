import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp_apps.auth.models import AccountsRepository, IdentitiesRepository


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def accounts(factory):
    return AccountsRepository(factory)


@pytest.fixture
def identities(factory):
    return IdentitiesRepository(factory)


async def password_identity(identities, account, subject=None, password_hash="$argon2id$x"):
    return await identities.create(
        {
            "account_id": account.id,
            "method": "password",
            "issuer": "",
            "subject": subject or account.username,
            "password_hash": password_hash,
        }
    )


async def test_the_password_identity_of_a_login_comes_with_its_account(accounts, identities):
    alice = await accounts.create({"username": "alice"})
    await password_identity(identities, alice)

    identity, account = await identities.find_password("alice")

    assert (identity.subject, identity.password_hash, account.id) == ("alice", "$argon2id$x", alice.id)
    assert identity.last_sign_in_at is None and identity.created_at is not None


async def test_an_unknown_login_has_no_identity(identities):
    assert await identities.find_password("nobody") is None


async def test_a_method_issuer_and_subject_belong_to_one_identity(accounts, identities):
    alice = await accounts.create({"username": "alice"})
    bob = await accounts.create({"username": "bob"})
    await password_identity(identities, alice, subject="login")

    with pytest.raises(IntegrityError):
        await password_identity(identities, bob, subject="login")


async def test_the_same_subject_may_exist_at_two_issuers(accounts, identities):
    alice = await accounts.create({"username": "alice"})
    for issuer in ("https://one.example", "https://two.example"):
        await identities.create(
            {"account_id": alice.id, "method": "oidc", "issuer": issuer, "subject": "42", "password_hash": None}
        )


async def test_an_oidc_identity_is_not_a_password_identity(accounts, identities):
    alice = await accounts.create({"username": "alice"})
    await identities.create(
        {"account_id": alice.id, "method": "oidc", "issuer": "https://idp.example", "subject": "alice"}
    )

    assert await identities.find_password("alice") is None


async def test_the_password_hash_and_the_last_sign_in_are_updated(accounts, identities):
    from datetime import UTC, datetime

    alice = await accounts.create({"username": "alice"})
    identity = await password_identity(identities, alice)
    now = datetime(2026, 10, 25, tzinfo=UTC)

    await identities.set_password_hash(identity.id, "$argon2id$y")
    await identities.signed_in(identity.id, now)

    found, _ = await identities.find_password("alice")
    assert (found.password_hash, found.last_sign_in_at) == ("$argon2id$y", now)
