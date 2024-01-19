from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Float, String, select
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship, selectinload

from harp.core.models.transactions import Transaction as TransactionModel

from .base import Base, Repository
from .flags import FLAGS_BY_TYPE, Flag

if TYPE_CHECKING:
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


class TransactionsRepository(Repository):
    Type = Transaction

    def select(self, /, *, with_messages=False, with_user_flags=False):
        query = select(self.Type)

        # should we join transaction messages?
        if with_messages:
            query = query.options(
                joinedload(
                    self.Type.messages,
                )
            )

        # should we select flags for given user id?
        if with_user_flags:
            query = query.options(
                selectinload(
                    self.Type.flags.and_(
                        Flag.user_id == with_user_flags,
                    )
                )
            )

        return query

    async def find_one_by_id(self, id: str, /, **select_kwargs) -> Transaction:
        async with self.session() as session:
            return (
                (
                    await session.execute(
                        self.select(**select_kwargs).where(
                            self.Type.id == id,
                        )
                    )
                )
                .unique()
                .scalar_one()
            )
