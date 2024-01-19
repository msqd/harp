from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from .flags import Flag


class User(Base):
    __tablename__ = "sa_users"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    username = mapped_column(String(32), unique=True)

    flags: Mapped[List["Flag"]] = relationship(back_populates="user", cascade="all, delete-orphan")
