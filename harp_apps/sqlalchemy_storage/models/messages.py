from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from harp.http import get_serializer_for
from harp.models.messages import Message as MessageModel

from .base import Base, Repository, with_session

if TYPE_CHECKING:
    from .transactions import Transaction


class Message(Base):
    __tablename__ = "messages"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    kind = mapped_column(String(10))
    summary = mapped_column(String(255))
    headers = mapped_column(String(40))
    body = mapped_column(String(40))
    created_at = mapped_column(TIMESTAMP(timezone=True))

    transaction_id = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"))
    transaction: Mapped["Transaction"] = relationship(back_populates="messages")

    def to_model(self):
        return MessageModel(
            id=self.id,
            transaction_id=self.transaction_id,
            kind=self.kind,
            summary=self.summary,
            headers=self.headers,
            body=self.body,
            created_at=self.created_at.replace(tzinfo=UTC) if self.created_at else self.created_at,
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
        return await super().create(values, session=session)
