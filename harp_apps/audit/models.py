from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import JSON, TIMESTAMP, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from harp_apps.storage.models.base import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AuditEvent(Base):
    """
    One thing an account did to HARP. Appended in the commit of the action, never updated, deleted only by retention.

    Neither the actor nor the target is a foreign key: a row outlives what it refers to, which is why the labels are
    copied.
    """

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_target", "target_type", "target_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=_now, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    outcome: Mapped[str] = mapped_column(String(16))
    actor_account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_via: Mapped[str] = mapped_column(String(16))
    actor_via_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
