from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, List

from sqlalchemy import TIMESTAMP, Boolean, Column, Float, ForeignKey, Integer, String, Table, exists, insert
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from harp.models.transactions import Transaction as TransactionModel

from .base import Base, Repository, with_session
from .flags import FLAGS_BY_TYPE, UserFlag
from .tags import TagValue

if TYPE_CHECKING:
    from .messages import Message

transaction_tag_values_association_table = Table(
    "trans_tag_values",
    Base.metadata,
    Column(
        "transaction_id",
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("value_id", ForeignKey("tag_values.id", ondelete="CASCADE"), primary_key=True),
)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(String(27), primary_key=True, unique=True)
    type: Mapped[str] = mapped_column(String(10), index=True)
    endpoint: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), index=True)
    finished_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    elapsed: Mapped[float] = mapped_column(Float(), nullable=True)
    tpdex: Mapped[int] = mapped_column(Integer(), nullable=True)
    x_method: Mapped[str] = mapped_column(String(16), nullable=True, index=True)
    x_status_class: Mapped[str] = mapped_column(String(3), nullable=True, index=True)
    x_cached: Mapped[str] = mapped_column(String(32), nullable=True)
    x_no_cache: Mapped[bool] = mapped_column(Boolean(), nullable=True, default=False)

    messages: Mapped[List["Message"]] = relationship(
        back_populates="transaction",
        order_by="Message.id",
        cascade="all, delete",
        passive_deletes=True,
    )
    flags: Mapped[List["UserFlag"]] = relationship(
        back_populates="transaction",
        cascade="all, delete",
        passive_deletes=True,
    )
    _tag_values: Mapped[List["TagValue"]] = relationship(
        secondary=transaction_tag_values_association_table,
        cascade="all, delete",
        passive_deletes=True,
    )

    @property
    def tags(self):
        return {tag_value.tag.name: tag_value.value for tag_value in self._tag_values}

    def to_model(self, with_user_flags=False):
        return TransactionModel(
            id=self.id,
            type=self.type,
            endpoint=self.endpoint,
            started_at=self.started_at.replace(tzinfo=UTC),
            finished_at=(self.finished_at.replace(tzinfo=UTC) if self.finished_at else self.finished_at),
            elapsed=self.elapsed,
            tpdex=self.tpdex,
            extras=dict(
                method=self.x_method,
                status_class=self.x_status_class,
                cached=bool(self.x_cached),
                no_cache=bool(self.x_no_cache),
                **(
                    {
                        "flags": list(
                            set(
                                filter(
                                    None,
                                    (FLAGS_BY_TYPE.get(flag.type, None) for flag in self.flags),
                                )
                            )
                        )
                    }
                    if with_user_flags
                    else {}
                ),
            ),
            messages=([message.to_model() for message in self.messages] if self.messages else []),
            tags=self.tags,
        )


class TransactionsRepository(Repository[Transaction]):
    Type = Transaction

    def __init__(self, session_factory, /, tags=None, tag_values=None):
        super().__init__(session_factory)

        self.tags = tags
        self.tag_values = tag_values

    def select(self, /, *, with_messages=False, with_user_flags=False, with_tags=False):
        query = super().select()

        # should we join transaction messages?
        if with_messages:
            query = query.options(
                selectinload(
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

    def delete_old(self, old_after: timedelta):
        threshold = datetime.now(UTC) - old_after
        no_flags = ~exists().where(UserFlag.transaction_id == self.Type.id)
        return self.delete().where((self.Type.started_at < threshold) & no_flags)

    @with_session
    async def create(self, values: dict | TransactionModel, /, *, session=None):
        # convert model to dict
        if isinstance(values, TransactionModel):
            values = values.as_storable_dict()
        tags = values.pop("tags", {})
        transaction = await super().create(values, session=session)
        if len(tags):
            await self.set_tags(transaction, tags, session=session)
        return transaction

    @with_session
    async def set_tags(self, transaction: Transaction, tags: dict, /, *, session=None):
        if not self.tags:
            raise ValueError("Tags repository is not available.")
        if not self.tag_values:
            raise ValueError("Tag values repository is not available.")

        values = []
        for name, value in tags.items():
            db_tag = await self.tags.find_or_create_one({"name": name}, session=session)
            db_value = await self.tag_values.find_or_create_one({"tag_id": db_tag.id, "value": value}, session=session)
            values.append(
                {
                    "transaction_id": transaction.id,
                    "value_id": db_value.id,
                }
            )

        if len(values):
            await session.execute(insert(transaction_tag_values_association_table), values)
            await session.commit()

        return transaction
