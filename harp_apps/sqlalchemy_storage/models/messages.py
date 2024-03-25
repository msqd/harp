from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from harp.http import get_serializer_for
from harp.models.messages import Message as MessageModel

from .base import Base, Repository

if TYPE_CHECKING:
    from .transactions import Transaction


class Message(Base):
    __tablename__ = "sa_messages"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    transaction_id = mapped_column(ForeignKey("sa_transactions.id"))
    kind = mapped_column(String(10))
    summary = mapped_column(String(255))
    headers = mapped_column(String(40))
    body = mapped_column(String(40))
    created_at = mapped_column(DateTime())

    transaction: Mapped["Transaction"] = relationship(back_populates="messages")

    def to_model(self):
        return MessageModel(
            id=self.id,
            transaction_id=self.transaction_id,
            kind=self.kind,
            summary=self.summary,
            headers=self.headers,
            body=self.body,
            created_at=self.created_at,
        )

    @classmethod
    def from_models(cls, transaction, message, headers, content):
        serializer = get_serializer_for(message)

        obj = cls()
        obj.transaction_id = transaction.id
        obj.kind = message.kind
        obj.summary = serializer.summary
        obj.headers = headers.id
        obj.body = content.id
        obj.created_at = message.created_at.astimezone(UTC).replace(tzinfo=None)
        return obj


class MessagesRepository(Repository[Message]):
    Type = Message
