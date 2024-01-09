from typing import List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Transactions(Base):
    __tablename__ = "sa_transactions"

    id = mapped_column(String(27), primary_key=True, unique=True)
    type = mapped_column(String(10), index=True)
    endpoint = mapped_column(String(32), nullable=True, index=True)
    started_at = mapped_column(DateTime(), index=True)
    finished_at = mapped_column(DateTime(), nullable=True)
    elapsed = mapped_column(Float(), nullable=True)
    x_method = mapped_column(String(16), nullable=True, index=True)
    x_status_class = mapped_column(String(3), nullable=True, index=True)

    messages: Mapped[List["Messages"]] = relationship(back_populates="transaction")


class Blobs(Base):
    __tablename__ = "sa_blobs"

    id = mapped_column(String(40), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))


class Messages(Base):
    __tablename__ = "sa_messages"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    transaction_id = mapped_column(ForeignKey("sa_transactions.id"))
    kind = mapped_column(String(10))
    summary = mapped_column(String(255))
    headers = mapped_column(String(40))
    body = mapped_column(String(40))
    created_at = mapped_column(DateTime())

    transaction: Mapped["Transactions"] = relationship(back_populates="messages")
