"""Accounts: what signs in to HARP, and holds a role.

The table descends from storage's ``users`` (favourites keep their author), which is why the model sits on storage's
``Base``: every model shares it.
"""

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    case,
    func,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import TypeDecorator

from harp.security.actor import Role
from harp_apps.storage.models.base import Base, Repository

if TYPE_CHECKING:
    from harp_apps.storage.models.flags import UserFlag

#: The account that authors the favourites recorded before accounts had roles. It never signs in.
SYSTEM_ACCOUNT_USERNAME = "anonymous"

#: A system account that records that the users declared in the configuration (Basic) were imported. It never signs in.
IMPORT_MARKER_USERNAME = "basic-import"

#: Names of the system accounts: no person or machine may take them.
RESERVED_USERNAMES = frozenset({SYSTEM_ACCOUNT_USERNAME, IMPORT_MARKER_USERNAME})

#: ``disabled_reason`` of the accounts the migration disabled, waiting for the one-time import.
MIGRATED = "migrated"


_USERNAME_SHAPE = re.compile(r"[A-Za-z0-9._@+-]{1,64}")


class UsernameRefused(ValueError):
    """The username cannot be used for a new account; the message is safe to show."""


def check_username(username: str) -> None:
    """Raises :class:`UsernameRefused` unless a new account may have this name: not a system account's, and short, with
    nothing a login form or a log line could mistake."""
    if username in RESERVED_USERNAMES:
        raise UsernameRefused("This username is reserved.")
    if not _USERNAME_SHAPE.fullmatch(username):
        raise UsernameRefused("A username has 1 to 64 letters, digits, or any of . _ @ + -")


class ReservedUsernameError(ValueError):
    def __init__(self, username):
        super().__init__(f"The username {username!r} is reserved for a system account.")


class AccountKind(StrEnum):
    PERSON = "person"
    MACHINE = "machine"
    SYSTEM = "system"


class RoleType(TypeDecorator):
    """A :class:`~harp.security.actor.Role`, stored as its label."""

    impl = String(16)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else Role(value).label

    def process_result_value(self, value, dialect):
        return None if value is None else Role.parse(value)


class UTCTimestamp(TypeDecorator):
    """A timestamp with time zone, read back timezone aware on every database (SQLite drops the zone)."""

    impl = TIMESTAMP(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class Account(Base):
    __tablename__ = "auth_accounts"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    username = mapped_column(String(255), unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(320), unique=True, nullable=True)
    kind: Mapped[AccountKind] = mapped_column(
        Enum(
            AccountKind,
            native_enum=False,
            length=16,
            create_constraint=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=AccountKind.PERSON,
    )
    role: Mapped[Role] = mapped_column(RoleType(), nullable=False, default=Role.VIEWER)
    created_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False, server_default=func.now())
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)
    #: Who disabled the account: ``migrated`` (the migration, until the import) or ``operator``.
    disabled_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    flags: Mapped[List["UserFlag"]] = relationship(
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )

    __table_args__ = (
        # emails are compared as they are stored: unique means unique whatever the case
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("kind IN ('person', 'machine', 'system')", name="kind"),
        CheckConstraint("role IN ('viewer', 'editor', 'admin')", name="role"),
    )

    @validates("email")
    def _lower_case_email(self, key, value):
        return None if value is None else value.lower()


class AccountsRepository(Repository):
    Type = Account

    async def find_one_by_username(self, username: str) -> Account:
        """The account named ``username``, or the system account when there is none (it authors anonymous favourites)."""
        async with self.session_factory() as session:
            try:
                return (
                    (await session.execute(select(self.Type).where(Account.username == username))).unique().scalar_one()
                )
            except NoResultFound:
                return (
                    (await session.execute(select(self.Type).where(Account.username == SYSTEM_ACCOUNT_USERNAME)))
                    .unique()
                    .scalar_one()
                )

    async def find_all(self) -> list[Account]:
        async with self.session_factory() as session:
            return list((await session.execute(select(Account).order_by(Account.id))).scalars())

    async def _import_done(self) -> bool:
        """Whether the import ran: a system account holds the marker. A person with that name is refused."""
        async with self.session_factory() as session:
            kind = (
                await session.execute(select(Account.kind).where(Account.username == IMPORT_MARKER_USERNAME))
            ).scalar_one_or_none()
        if kind is not None and kind != AccountKind.SYSTEM:
            raise ReservedUsernameError(IMPORT_MARKER_USERNAME)
        return kind is not None

    async def import_basic_users(self, usernames) -> bool:
        """
        Imports the users declared in the configuration (decision 21), once for the database. Missing ones are created
        as enabled Admin people; the ones the migration left disabled are enabled as Admin. Any other account is left as
        it is, so what the Operator decided before or during the import (a role, a disabling) wins, and later calls do
        nothing. Returns whether it ran.
        """
        if await self._import_done():
            return False
        async with self.session_factory() as session:
            session.add(Account(username=IMPORT_MARKER_USERNAME, kind=AccountKind.SYSTEM, role=Role.VIEWER))
            try:
                await session.flush()
            except IntegrityError:
                # the marker is unique: another process imported meanwhile
                await session.rollback()
                return False
            for username in usernames:
                exists = (await session.execute(select(Account.id).where(Account.username == username))).first()
                if exists is None:
                    session.add(Account(username=username, kind=AccountKind.PERSON, role=Role.ADMIN))
                else:
                    # conditional on the mark, so a change landing meanwhile is never overwritten
                    await session.execute(
                        update(Account)
                        .where(
                            Account.username == username,
                            Account.kind != AccountKind.SYSTEM,
                            Account.disabled_reason == MIGRATED,
                        )
                        .values(role=Role.ADMIN, disabled_at=None, disabled_reason=None)
                    )
            await session.commit()
            return True

    async def update_account(self, username: str, **values) -> None:
        """
        Changes a person or machine account (not a system one) with a single UPDATE. Disabling or enabling records who
        decided (``operator``) or clears it; any change consumes the mark of the migration, so the import leaves the
        account alone. Raises NoResultFound if there is none.
        """
        reason = Account.disabled_reason
        if "disabled_at" in values:
            reason = "operator" if values["disabled_at"] is not None else None
        else:
            reason = case((Account.disabled_reason == MIGRATED, "operator"), else_=Account.disabled_reason)
        async with self.session_factory() as session:
            result = await session.execute(
                update(Account)
                .where(Account.username == username, Account.kind != AccountKind.SYSTEM)
                .values(**values, disabled_reason=reason)
            )
            await session.commit()
        if result.rowcount == 0:
            raise NoResultFound(username)


#: The sign-in method of a password identity: ``issuer`` is empty and ``subject`` is the username.
PASSWORD_METHOD = "password"  # pragma: allowlist secret


class Identity(Base):
    """The link between an account and one sign-in method, such as "alice, with a password"."""

    __tablename__ = "auth_identities"

    id = mapped_column(Integer(), primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    #: The OIDC ``iss``, empty for a password.
    issuer: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    #: The login of a password, the ``sub`` of an OIDC provider.
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    #: PHC string, for passwords only.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False, server_default=func.now())
    last_sign_in_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)

    __table_args__ = (UniqueConstraint("method", "issuer", "subject"),)


class Session(Base):
    """One browser signed in to an account through one identity. The cookie holds a secret, only its hash is kept."""

    __tablename__ = "auth_sessions"

    id = mapped_column(Integer(), primary_key=True, autoincrement=True)
    #: SHA-256 (hex) of the secret in the cookie: reading the table gives nobody a session.
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identity_id: Mapped[int] = mapped_column(ForeignKey("auth_identities.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False, server_default=func.now())
    #: Written at most once a minute.
    last_seen_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)


class Invitation(Base):
    """An admin's single-use offer of an account with a role. Here only the setup link uses it (no ``invited_by``)."""

    __tablename__ = "auth_invitations"

    id = mapped_column(Integer(), primary_key=True, autoincrement=True)
    #: SHA-256 (hex) of the secret in the link.
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role: Mapped[Role] = mapped_column(RoleType(), nullable=False)
    expected_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    #: Who offered it; empty for the setup link, which nobody offered.
    invited_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="SET NULL"), nullable=True
    )
    #: The account it created, filled when it is accepted.
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(UTCTimestamp(), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCTimestamp(), nullable=True)

    __table_args__ = (CheckConstraint("role IN ('viewer', 'editor', 'admin')", name="role"),)

    @validates("expected_email")
    def _lower_case_expected_email(self, key, value):
        return None if value is None else value.lower()


class IdentitiesRepository(Repository):
    Type = Identity

    async def find_password(self, username: str) -> Optional[tuple[Identity, Account]]:
        """The password identity of ``username`` and its account, or None."""
        async with self.session_factory() as session:
            row = (
                await session.execute(
                    select(Identity, Account)
                    .join(Account, Account.id == Identity.account_id)
                    .where(
                        Identity.method == PASSWORD_METHOD,
                        Identity.issuer == "",
                        Identity.subject == username,
                    )
                )
            ).first()
        return None if row is None else (row[0], row[1])

    async def find_password_of_account(self, account_id: int) -> Optional[Identity]:
        async with self.session_factory() as session:
            return (
                await session.execute(
                    select(Identity).where(Identity.account_id == account_id, Identity.method == PASSWORD_METHOD)
                )
            ).scalar_one_or_none()

    async def set_password_hash(self, identity_id: int, password_hash: str) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(Identity).where(Identity.id == identity_id).values(password_hash=password_hash)
            )
            await session.commit()

    async def signed_in(self, identity_id: int, at: datetime) -> None:
        async with self.session_factory() as session:
            await session.execute(update(Identity).where(Identity.id == identity_id).values(last_sign_in_at=at))
            await session.commit()


class SessionsRepository(Repository):
    Type = Session

    async def find_by_secret_hash(self, secret_hash: str) -> Optional[Session]:
        async with self.session_factory() as session:
            return (
                await session.execute(select(Session).where(Session.secret_hash == secret_hash))
            ).scalar_one_or_none()

    async def seen(self, session_id: int, at: datetime) -> None:
        async with self.session_factory() as session:
            await session.execute(update(Session).where(Session.id == session_id).values(last_seen_at=at))
            await session.commit()

    async def _revoke(self, at: datetime, *criteria) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                update(Session).where(Session.revoked_at.is_(None), *criteria).values(revoked_at=at)
            )
            await session.commit()
        return result.rowcount

    async def revoke(self, session_id: int, at: datetime) -> int:
        """Ends one session (sign out). Returns how many were open."""
        return await self._revoke(at, Session.id == session_id)

    async def revoke_all(self, account_id: int, at: datetime) -> int:
        """Ends every open session of the account (sign out everywhere), with a single UPDATE."""
        return await self._revoke(at, Session.account_id == account_id)

    async def revoke_others(self, account_id: int, keep_id: int, at: datetime) -> int:
        """Ends every open session of the account but one."""
        return await self._revoke(at, Session.account_id == account_id, Session.id != keep_id)


class InvitationsRepository(Repository):
    Type = Invitation
