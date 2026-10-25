"""The setup link: how the first Admin gets in.

While no Admin exists, HARP logs a link at each start. It is the minimal form of an **invitation** (decision 7): a row of
``auth_invitations`` for the Admin role, nobody offered it (``invited_by`` is empty), single-use, valid for
``setup_link_hours`` (72), stored as the SHA-256 of its secret. Invitations for other accounts (#1523) are the same row
with an author, an expected email and another role, and the same acceptance: nothing here needs migrating, only
generalising.

The secret is in the fragment of the URL, which a browser never sends to a server: it reaches neither an access log nor a
``Referer``. The page sends it in the body of the request that accepts the link.
"""

import secrets
from datetime import UTC, datetime
from typing import Callable, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from harp.security.actor import Role
from harp_apps.auth.models import (
    PASSWORD_METHOD,
    UsernameRefused,
    check_username,
    login_of,
    Account,
    AccountKind,
    Identity,
    Invitation,
)
from harp_apps.auth.passwords import PasswordHasher, check_policy
from harp_apps.auth.sessions import SECRET_BYTES, SECRET_SHAPE, SessionsService, hash_secret
from harp_apps.auth.settings import AuthSettings
from harp_apps.auth.signin import Signed
from harp_apps.storage.types import IStorage


class SetupLinkRefused(Exception):
    """Unknown, used, revoked or expired link, or an Admin exists already: one answer for all of them."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _admin_exists():
    return (
        select(Account.id)
        .where(Account.role == Role.ADMIN, Account.kind == AccountKind.PERSON, Account.disabled_at.is_(None))
        .limit(1)
        .exists()
    )


def _unused_setup_invitations():
    return (
        Invitation.invited_by.is_(None),
        Invitation.role == Role.ADMIN,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
    )


class SetupLink:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        hasher: PasswordHasher,
        sessions: SessionsService,
        settings: AuthSettings,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ):
        self.session_factory = session_factory
        self.hasher = hasher
        self.sessions = sessions
        self.settings = settings
        self.clock = clock

    @classmethod
    def from_storage(
        cls, storage: IStorage, sessions: SessionsService, hasher: PasswordHasher, settings: AuthSettings
    ) -> "SetupLink":
        return cls(storage.accounts.session_factory, hasher, sessions, settings)

    async def publish(self, base_url: str) -> Optional[str]:
        """
        The link to log, or None when an Admin exists. A link still unused is revoked, so only the latest one works: the
        one in the logs of this start.
        """
        now = self.clock()
        secret = secrets.token_urlsafe(SECRET_BYTES)
        async with self.session_factory() as session:
            if (await session.execute(select(_admin_exists()))).scalar():
                return None
            await session.execute(update(Invitation).where(*_unused_setup_invitations()).values(revoked_at=now))
            session.add(
                Invitation(
                    secret_hash=hash_secret(secret),
                    role=Role.ADMIN,
                    created_at=now,
                    expires_at=now + self.settings.setup_link_lifetime,
                )
            )
            await session.commit()
        return f"{base_url.rstrip('/')}/setup#{secret}"

    async def accept(self, secret: str, username: str, password: str, *, ip: str, user_agent: Optional[str]) -> Signed:
        """
        Creates the first Admin with a password and signs it in. The link is used up only if everything else is
        right: a weak password or a taken username leaves it valid for another try.

        :raises SetupLinkRefused: the link is not valid (any reason).
        :raises UsernameRefused: the username cannot be used.
        :raises harp_apps.auth.passwords.PasswordPolicyError: the password is refused.
        """
        if not SECRET_SHAPE.fullmatch(secret):
            raise SetupLinkRefused()
        invitation_id = await self._valid_invitation(hash_secret(secret))
        check_username(username)
        check_policy(password)

        password_hash = await self.hasher.hash(password)
        now = self.clock()
        async with self.session_factory() as session:
            consumed = await session.execute(
                update(Invitation)
                .where(
                    Invitation.id == invitation_id,
                    *_unused_setup_invitations(),
                    Invitation.expires_at > now,
                )
                .values(accepted_at=now)
            )
            # an Admin may have appeared since the link was published (the account command): the link is void
            if consumed.rowcount != 1 or (await session.execute(select(_admin_exists()))).scalar():
                await session.rollback()
                raise SetupLinkRefused()
            account = Account(username=username, kind=AccountKind.PERSON, role=Role.ADMIN)
            session.add(account)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                raise UsernameRefused("This username is taken.") from None
            identity = Identity(
                account_id=account.id,
                method=PASSWORD_METHOD,
                issuer="",
                subject=login_of(username),
                password_hash=password_hash,
                last_sign_in_at=now,
            )
            session.add(identity)
            try:
                await session.flush()
            except IntegrityError:  # another account signs in under the same login, written otherwise
                await session.rollback()
                raise UsernameRefused("This username is taken.") from None
            await session.execute(
                update(Invitation).where(Invitation.id == invitation_id).values(account_id=account.id)
            )
            await session.commit()
            account_id, identity_id = account.id, identity.id

        opened, row = await self.sessions.open(account_id, identity_id, user_agent=user_agent, ip=ip)
        return Signed(opened, row)

    async def _valid_invitation(self, secret_hash: str) -> int:
        async with self.session_factory() as session:
            row = (
                await session.execute(
                    select(Invitation.id).where(
                        Invitation.secret_hash == secret_hash,
                        *_unused_setup_invitations(),
                        Invitation.expires_at > self.clock(),
                    )
                )
            ).scalar_one_or_none()
            if row is None or (await session.execute(select(_admin_exists()))).scalar():
                raise SetupLinkRefused()
            return row
