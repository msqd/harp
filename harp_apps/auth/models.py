"""Accounts: what signs in to HARP, and holds a role.

The table descends from storage's ``users`` (favourites keep their author), which is why the model sits on storage's
``Base``: every model shares it.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import TIMESTAMP, CheckConstraint, Enum, Integer, String, func, select
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

    async def import_basic_users(self, usernames) -> bool:
        """
        Imports the users declared in the configuration as enabled Admin people (decision 21), once for the database:
        later calls do nothing, so an account that was deleted, demoted or disabled stays so. Returns whether it ran.
        """
        try:
            async with self.session_factory() as session:
                if (
                    await session.execute(select(Account.id).where(Account.username == IMPORT_MARKER_USERNAME))
                ).first():
                    return False
                session.add(Account(username=IMPORT_MARKER_USERNAME, kind=AccountKind.SYSTEM, role=Role.VIEWER))
                for username in usernames:
                    account = (
                        await session.execute(select(Account).where(Account.username == username))
                    ).scalar_one_or_none()
                    if account is None:
                        session.add(Account(username=username, kind=AccountKind.PERSON, role=Role.ADMIN))
                    elif account.kind != AccountKind.SYSTEM:
                        account.role, account.disabled_at = Role.ADMIN, None
                await session.commit()
                return True
        except IntegrityError:
            # another process imported meanwhile
            return False

    async def update_account(self, username: str, **values) -> Account:
        """Changes a person or machine account (not a system one). Raises NoResultFound if there is none."""
        async with self.session_factory() as session:
            account = (
                await session.execute(
                    select(Account).where(Account.username == username, Account.kind != AccountKind.SYSTEM)
                )
            ).scalar_one()
            for key, value in values.items():
                setattr(account, key, value)
            await session.commit()
            return account
