"""audit events

Revision ID: 3f6b9c2a41d7
Revises:
Create Date: 2026-10-25 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f6b9c2a41d7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("audit",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor_account_id", sa.Integer(), nullable=True),
        sa.Column("actor_label", sa.String(length=255), nullable=True),
        sa.Column("actor_via", sa.String(length=16), nullable=False),
        sa.Column("actor_via_id", sa.String(length=64), nullable=True),
        sa.Column("actor_client", sa.String(length=255), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("target_label", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_occurred_at"), "audit_events", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_audit_events_actor_account_id"), "audit_events", ["actor_account_id"], unique=False)
    op.create_index("ix_audit_events_target", "audit_events", ["target_type", "target_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_target", table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_actor_account_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_occurred_at"), table_name="audit_events")
    op.drop_table("audit_events")
