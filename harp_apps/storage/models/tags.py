from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base
from .base import Repository


class Tag(Base):
    __tablename__ = "tags"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    name = mapped_column(String(64), nullable=False, unique=True)


class TagsRepository(Repository[Tag]):
    Type = Tag


class TagValue(Base):
    __tablename__ = "tag_values"
    __table_args__ = (UniqueConstraint("tag_id", "value", name=f"_{__tablename__[3:]}_uc"),)

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)

    tag_id = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    tag: Mapped["Tag"] = relationship()

    value = mapped_column(String(255), nullable=False)


class TagValuesRepository(Repository[TagValue]):
    Type = TagValue
