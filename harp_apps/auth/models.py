"""Accounts: what signs in to HARP, and holds a role.

The table descends from storage's ``users`` (favourites keep their author), which is why the model sits on storage's
``Base``: every model shares it.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import TIMESTAMP, CheckConstraint, Enum, Integer, String, case, func, select, update
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
