import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import AccountKind, AccountsRepository


@pytest.fixture
def accounts(sql_engine) -> AccountsRepository:
    return AccountsRepository(async_sessionmaker(sql_engine, expire_on_commit=False))


async def test_account_defaults_to_a_viewer_person(accounts):
    account = await accounts.create({"username": "alice"})

    assert (account.kind, account.role) == (AccountKind.PERSON, Role.VIEWER)
    assert account.created_at is not None
    assert account.last_seen_at is None
    assert account.disabled_at is None
    assert account.email is None


async def test_username_may_be_255_characters_long(accounts):
    account = await accounts.create({"username": "a" * 255})

    assert len((await accounts.find_one_by_id(account.id)).username) == 255


async def test_role_and_kind_survive_a_round_trip(accounts):
    await accounts.create({"username": "ci", "kind": AccountKind.MACHINE, "role": Role.EDITOR})

    account = await accounts.find_one({"username": "ci"})

    assert (account.kind, account.role) == (AccountKind.MACHINE, Role.EDITOR)


async def test_email_is_stored_lower_cased(accounts):
    await accounts.create({"username": "alice", "email": "Alice@Example.COM"})

    assert (await accounts.find_one({"username": "alice"})).email == "alice@example.com"


async def test_email_is_unique_whatever_its_case(accounts):
    await accounts.create({"username": "alice", "email": "alice@example.com"})

    with pytest.raises(IntegrityError):
        await accounts.create({"username": "alice2", "email": "ALICE@example.com"})


async def test_many_accounts_may_have_no_email(accounts):
    await accounts.create({"username": "alice"})
    await accounts.create({"username": "bob"})


async def test_username_is_unique(accounts):
    await accounts.create({"username": "alice"})

    with pytest.raises(IntegrityError):
        await accounts.create({"username": "alice"})


async def test_find_one_by_username_falls_back_to_the_system_account(accounts):
    await accounts.create({"username": "anonymous", "kind": AccountKind.SYSTEM})

    assert (await accounts.find_one_by_username("nobody")).username == "anonymous"
