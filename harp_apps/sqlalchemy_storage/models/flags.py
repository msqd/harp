from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Repository

if TYPE_CHECKING:
    from .transactions import Transaction
    from .users import User

FLAGS_BY_TYPE = {1: "favorite"}
FLAGS_BY_NAME = {v: k for k, v in FLAGS_BY_TYPE.items()}


class UserFlag(Base):
    __tablename__ = "trans_user_flags"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    type = mapped_column(Integer(), nullable=False)

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="flags")

    transaction_id = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    transaction: Mapped["Transaction"] = relationship(back_populates="flags")

    __table_args__ = (UniqueConstraint("user_id", "transaction_id", "type", name="_user_transaction_uc"),)


class FlagsRepository(Repository):
    Type = UserFlag
