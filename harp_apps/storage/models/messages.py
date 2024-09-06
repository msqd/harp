from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from harp.http import BaseMessage, get_serializer_for
from harp.models.messages import Message as MessageModel

from .base import Base, Repository, with_session

if TYPE_CHECKING:
    from .transactions import Transaction


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(10))
    summary: Mapped[str] = mapped_column(Text)
    headers: Mapped[str] = mapped_column(String(40))
    body: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"))
    transaction: Mapped["Transaction"] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_transaction_id", "transaction_id"),)

    def to_model(self):
        return MessageModel(
            id=self.id,
            transaction_id=self.transaction_id,
            kind=self.kind,
            summary=self.summary,
            headers=self.headers,
            body=self.body,
            created_at=(self.created_at.replace(tzinfo=UTC) if self.created_at else self.created_at),
        )

    @classmethod
    def from_models(cls, transaction, message: BaseMessage, headers, content):
        serializer = get_serializer_for(message)

        obj = cls()
        obj.transaction_id = transaction.id
        obj.kind = message.kind
        obj.summary = serializer.summary
        obj.headers = headers.id
        obj.body = content.id
        obj.created_at = message.created_at.astimezone(UTC)
        return obj


class MessagesRepository(Repository[Message]):
    Type = Message

    @with_session
    async def create(self, values: dict | MessageModel, /, *, session):
        if isinstance(values, MessageModel):
            values = dict(
                id=values.id,
                transaction_id=values.transaction_id,
                kind=values.kind,
                summary=values.summary,
                headers=values.headers,
                body=values.body,
                created_at=values.created_at,
            )

        if not values.get("created_at"):
            values["created_at"] = datetime.now(UTC)

        return await super().create(values, session=session)
