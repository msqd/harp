from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import (
    AccountKind,
    AccountsRepository,
    IdentitiesRepository,
    Invitation,
    SessionsRepository,
)
from harp_apps.auth.passwords import PasswordHasher, PasswordPolicyError
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.settings import AuthSettings
from harp_apps.auth.setup import SetupLink, SetupLinkRefused, UsernameRefused

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


class Clock:
    now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def factory(sql_engine):
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def setup(factory, clock) -> SetupLink:
    settings = AuthSettings()
    return SetupLink(
        factory,
        PasswordHasher(),
        SessionsService(SessionsRepository(factory), settings, clock=clock),
        settings,
        clock=clock,
    )


async def invitations(factory):
    async with factory() as session:
        return list((await session.execute(select(Invitation).order_by(Invitation.id))).scalars())


def secret_of(link: str) -> str:
    assert "#" in link
    return link.split("#", 1)[1]


async def test_a_link_is_published_while_no_admin_exists(setup):
    link = await setup.publish("http://localhost:4080")

    assert link.startswith("http://localhost:4080/setup#") and len(secret_of(link)) >= 43


async def test_the_secret_stays_out_of_the_path_and_the_query(setup):
    link = await setup.publish("http://localhost:4080")

    path = link.split("#", 1)[0]
    assert secret_of(link) not in path and "?" not in path


async def test_the_link_is_an_invitation_to_the_admin_role_valid_72_hours_stored_hashed(setup, factory):
    link = await setup.publish("http://localhost:4080")

    (invitation,) = await invitations(factory)
    assert invitation.role is Role.ADMIN and invitation.invited_by is None
    assert invitation.expires_at == NOW + timedelta(hours=72)
    assert secret_of(link) not in (invitation.secret_hash,) and len(invitation.secret_hash) == 64


async def test_the_lifetime_is_a_setting(factory, clock):
    settings = AuthSettings(setup_link_hours=1)
    setup = SetupLink(
        factory, PasswordHasher(), SessionsService(SessionsRepository(factory), settings), settings, clock=clock
    )

    await setup.publish("http://x")

    assert (await invitations(factory))[0].expires_at == NOW + timedelta(hours=1)


async def test_a_new_link_replaces_the_unused_one_at_each_boot(setup, factory):
    first = await setup.publish("http://localhost:4080")
    second = await setup.publish("http://localhost:4080")

    assert secret_of(first) != secret_of(second)
    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret_of(first), "root", PASSWORD, ip="1.2.3.4", user_agent=None)
    assert (await setup.accept(secret_of(second), "root", PASSWORD, ip="1.2.3.4", user_agent=None)).secret


async def test_no_link_is_published_once_an_admin_exists(setup, factory):
    await AccountsRepository(factory).create({"username": "root", "role": Role.ADMIN})

    assert await setup.publish("http://localhost:4080") is None
    assert await invitations(factory) == []


async def test_a_disabled_admin_is_not_an_admin(setup, factory):
    accounts = AccountsRepository(factory)
    await accounts.create({"username": "root", "role": Role.ADMIN})
    await accounts.update_account("root", disabled_at=NOW)

    assert await setup.publish("http://localhost:4080") is not None


@pytest.mark.parametrize("role", [Role.VIEWER, Role.EDITOR])
async def test_other_roles_are_not_admins(setup, factory, role):
    await AccountsRepository(factory).create({"username": "someone", "role": role})

    assert await setup.publish("http://localhost:4080") is not None


async def test_a_machine_admin_is_not_a_way_in(setup, factory):
    await AccountsRepository(factory).create({"username": "ci", "role": Role.ADMIN, "kind": AccountKind.MACHINE})

    assert await setup.publish("http://localhost:4080") is not None


async def test_accepting_creates_the_admin_with_a_password_and_signs_it_in(setup, factory):
    link = await setup.publish("http://localhost:4080")

    signed = await setup.accept(secret_of(link), "root", PASSWORD, ip="1.2.3.4", user_agent="UA")

    account = await AccountsRepository(factory).find_one({"username": "root"})
    assert (account.role, account.kind, account.disabled_at) == (Role.ADMIN, AccountKind.PERSON, None)
    identity, _ = await IdentitiesRepository(factory).find_password("root")
    assert identity.password_hash.startswith("$argon2id$") and identity.account_id == account.id
    assert signed.session.account_id == account.id and signed.session.identity_id == identity.id
    (invitation,) = await invitations(factory)
    assert invitation.accepted_at == NOW and invitation.account_id == account.id


async def test_a_link_is_single_use(setup):
    secret = secret_of(await setup.publish("http://localhost:4080"))
    await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)

    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret, "root2", PASSWORD, ip="1.2.3.4", user_agent=None)


async def test_concurrent_acceptances_create_one_admin(setup, factory):
    import asyncio

    secret = secret_of(await setup.publish("http://localhost:4080"))

    results = await asyncio.gather(
        *(setup.accept(secret, f"root{i}", PASSWORD, ip="1.2.3.4", user_agent=None) for i in range(4)),
        return_exceptions=True,
    )

    assert sum(not isinstance(r, Exception) for r in results) == 1
    admins = [a for a in await AccountsRepository(factory).find_all() if a.role is Role.ADMIN]
    assert len(admins) == 1


async def test_a_link_expires(setup, clock):
    secret = secret_of(await setup.publish("http://localhost:4080"))

    clock.now = NOW + timedelta(hours=72)

    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)


async def test_a_link_works_until_it_expires(setup, clock):
    secret = secret_of(await setup.publish("http://localhost:4080"))

    clock.now = NOW + timedelta(hours=71, minutes=59)

    assert (await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)).secret


@pytest.mark.parametrize("secret", ["", "x" * 43, "not a secret", "x" * 10_000])
async def test_a_guess_is_refused(setup, secret):
    await setup.publish("http://localhost:4080")

    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)


async def test_a_link_is_void_once_an_admin_exists_whatever_its_expiry(setup, factory):
    secret = secret_of(await setup.publish("http://localhost:4080"))
    await AccountsRepository(factory).create({"username": "recovered", "role": Role.ADMIN})

    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)
    assert [a.username for a in await AccountsRepository(factory).find_all()] == ["recovered"]


class TestTheLinkIsCheckedAgainWhereItIsUsedUp:
    """Between looking at the link and using it up, another request may have used it, or time, or an Admin, gone by: the
    update that consumes it checks again. Here the first look is made to say yes whatever happened since."""

    @pytest.fixture
    def blind(self, setup, monkeypatch):
        async def always_the_first(secret_hash):
            return 1

        monkeypatch.setattr(setup, "_valid_invitation", always_the_first)

    async def test_a_used_link(self, setup, blind):
        secret = secret_of(await setup.publish("http://localhost:4080"))
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)

        with pytest.raises(SetupLinkRefused):
            await setup.accept(secret, "root2", PASSWORD, ip="1.2.3.4", user_agent=None)

    async def test_an_expired_link(self, setup, blind, clock):
        secret = secret_of(await setup.publish("http://localhost:4080"))
        clock.now = NOW + timedelta(hours=73)

        with pytest.raises(SetupLinkRefused):
            await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)

    async def test_a_revoked_link(self, setup, blind, factory):
        secret = secret_of(await setup.publish("http://localhost:4080"))
        async with factory() as session:
            (invitation,) = (await session.execute(select(Invitation))).scalars()
            invitation.revoked_at = NOW
            await session.commit()

        with pytest.raises(SetupLinkRefused):
            await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)
        assert await AccountsRepository(factory).find_all() == []

    async def test_an_admin_who_appeared(self, setup, blind, factory):
        secret = secret_of(await setup.publish("http://localhost:4080"))
        await AccountsRepository(factory).create({"username": "recovered", "role": Role.ADMIN})

        with pytest.raises(SetupLinkRefused):
            await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)
        assert [a.username for a in await AccountsRepository(factory).find_all()] == ["recovered"]


async def test_a_revoked_link_is_refused(setup, factory):
    secret = secret_of(await setup.publish("http://localhost:4080"))
    async with factory() as session:
        (invitation,) = (await session.execute(select(Invitation))).scalars()
        invitation.revoked_at = NOW
        await session.commit()

    with pytest.raises(SetupLinkRefused):
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)


async def test_a_weak_password_does_not_use_the_link_up(setup):
    secret = secret_of(await setup.publish("http://localhost:4080"))

    with pytest.raises(PasswordPolicyError):
        await setup.accept(secret, "root", "short", ip="1.2.3.4", user_agent=None)

    assert (await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)).secret


@pytest.mark.parametrize("username", ["", "anonymous", "basic-import", "has space", "a" * 65, "tab\t", "new\nline"])
async def test_a_username_that_cannot_be_used_does_not_use_the_link_up(setup, username):
    secret = secret_of(await setup.publish("http://localhost:4080"))

    with pytest.raises(UsernameRefused):
        await setup.accept(secret, username, PASSWORD, ip="1.2.3.4", user_agent=None)

    assert (await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)).secret


async def test_a_taken_username_does_not_use_the_link_up(setup, factory):
    await AccountsRepository(factory).create({"username": "root", "role": Role.VIEWER})
    secret = secret_of(await setup.publish("http://localhost:4080"))

    with pytest.raises(UsernameRefused):
        await setup.accept(secret, "root", PASSWORD, ip="1.2.3.4", user_agent=None)

    assert (await setup.accept(secret, "boss", PASSWORD, ip="1.2.3.4", user_agent=None)).secret
