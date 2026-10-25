"""Accounts: what signs in to HARP, and holds a role.

The table descends from storage's ``users`` (favourites keep their author), which is why the model sits on storage's
``Base``: every model shares it.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import TIMESTAMP, CheckConstraint, Enum, Integer, String, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import TypeDecorator

from harp.security.actor import Role
from harp_apps.storage.models.base import Base, Repository

if TYPE_CHECKING:
    from harp_apps.storage.models.flags import UserFlag

#: The account that authors the favourites recorded before accounts had roles. It never signs in.
SYSTEM_ACCOUNT_USERNAME = "anonymous"


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
