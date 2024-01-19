from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from harp.core.models.transactions import Transaction as TransactionModel

from .base import Base
from .flags import FLAGS_BY_TYPE

if TYPE_CHECKING:
    from .flags import Flag
    from .messages import Message


class Transaction(Base):
    __tablename__ = "sa_transactions"

    id = mapped_column(String(27), primary_key=True, unique=True)
    type = mapped_column(String(10), index=True)
    endpoint = mapped_column(String(32), nullable=True, index=True)
    started_at = mapped_column(DateTime(), index=True)
    finished_at = mapped_column(DateTime(), nullable=True)
    elapsed = mapped_column(Float(), nullable=True)
    x_method = mapped_column(String(16), nullable=True, index=True)
    x_status_class = mapped_column(String(3), nullable=True, index=True)

    messages: Mapped[List["Message"]] = relationship(back_populates="transaction")
    flags: Mapped[List["Flag"]] = relationship(back_populates="transaction", cascade="all, delete-orphan")

    def to_model(self, with_flags=False):
        return TransactionModel(
            id=self.id,
            type=self.type,
            endpoint=self.endpoint,
            started_at=self.started_at,
            finished_at=self.finished_at,
            elapsed=self.elapsed,
            extras=dict(
                method=self.x_method,
                status_class=self.x_status_class,
                **(
                    {"flags": list(set(filter(None, (FLAGS_BY_TYPE.get(flag.type, None) for flag in self.flags))))}
                    if with_flags
                    else {}
                ),
            ),
            messages=[message.to_model() for message in self.messages] if self.messages else [],
        )
