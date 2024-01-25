from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship, selectinload

from harp.models.transactions import Transaction as TransactionModel

from .base import Base, Repository
from .flags import FLAGS_BY_TYPE, UserFlag
from .tags import TagValue

if TYPE_CHECKING:
    from .messages import Message

transaction_tag_values_association_table = Table(
    "sa_trans_tag_values",
    Base.metadata,
    Column("transaction_id", ForeignKey("sa_transactions.id"), primary_key=True),
    Column("value_id", ForeignKey("sa_tag_values.id"), primary_key=True),
)


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

    messages: Mapped[List["Message"]] = relationship(back_populates="transaction", order_by="Message.id")
    flags: Mapped[List["UserFlag"]] = relationship(back_populates="transaction", cascade="all, delete-orphan")
    _tag_values: Mapped[List["TagValue"]] = relationship(secondary=transaction_tag_values_association_table)

    def to_model(self, with_user_flags=False):
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
                    if with_user_flags
                    else {}
                ),
            ),
            messages=[message.to_model() for message in self.messages] if self.messages else [],
            tags=self.tags,
        )

    @property
    def tags(self):
        return {tag_value.tag.name: tag_value.value for tag_value in self._tag_values}


class TransactionsRepository(Repository[Transaction]):
    Type = Transaction

    def select(self, /, *, with_messages=False, with_user_flags=False, with_tags=False):
        query = super().select()

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
                        UserFlag.user_id == with_user_flags,
                    )
                )
            )

        # should we select tags?
        if with_tags:
            query = query.options(
                selectinload(
                    self.Type._tag_values,
                ).joinedload(TagValue.tag)
            )

        return query
