from datetime import UTC
from typing import List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from harp.core.models.messages import Message as MessageModel
from harp.core.models.transactions import Transaction as TransactionModel


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "sa_users"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    username = mapped_column(String(32), unique=True)


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

    def to_model(self):
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
            ),
            messages=[message.to_model() for message in self.messages] if self.messages else [],
        )


class Blob(Base):
    __tablename__ = "sa_blobs"

    id = mapped_column(String(40), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))


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
        obj = cls()
        obj.transaction_id = transaction.id
        obj.kind = message.kind
        obj.summary = message.serialized_summary
        obj.headers = headers.id
        obj.body = content.id
        obj.created_at = message.created_at.astimezone(UTC).replace(tzinfo=None)
        return obj
