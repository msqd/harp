from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base
from .base import Repository

if TYPE_CHECKING:
    from .flags import UserFlag


class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    username = mapped_column(String(32), unique=True)

    flags: Mapped[List["UserFlag"]] = relationship(
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )


class UsersRepository(Repository):
    Type = User

    async def find_one_by_username(self, username: str) -> User:
        async with self.session_factory() as session:
            try:
                return (await session.execute(select(self.Type).where(User.username == username))).unique().scalar_one()
            except NoResultFound:
                return (
                    (await session.execute(select(self.Type).where(User.username == "anonymous"))).unique().scalar_one()
                )
