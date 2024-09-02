"""auto-generated migration

Revision ID: 248285939c4c
Revises:
Create Date: 2024-06-09 08:22:34.388765

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "248285939c4c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blobs",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=27), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=True),
        sa.Column("endpoint", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("elapsed", sa.Float(), nullable=True),
        sa.Column("apdex", sa.Integer(), nullable=True),
        sa.Column("x_method", sa.String(length=16), nullable=True),
        sa.Column("x_status_class", sa.String(length=3), nullable=True),
        sa.Column("x_cached", sa.String(length=32), nullable=True),
        sa.Column("x_no_cache", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_endpoint"), "transactions", ["endpoint"], unique=False)
    op.create_index(op.f("ix_transactions_started_at"), "transactions", ["started_at"], unique=False)
    op.create_index(op.f("ix_transactions_type"), "transactions", ["type"], unique=False)
    op.create_index(op.f("ix_transactions_x_method"), "transactions", ["x_method"], unique=False)
    op.create_index(
        op.f("ix_transactions_x_status_class"),
        "transactions",
        ["x_status_class"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=True),
        sa.Column("headers", sa.String(length=40), nullable=True),
        sa.Column("body", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("transaction_id", sa.String(length=27), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_table(
        "metric_values",
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metrics.id"],
        ),
        sa.PrimaryKeyConstraint("metric_id", "created_at"),
    )
    op.create_table(
        "tag_values",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("tag_id", "value", name="_tag_values_uc"),
    )
    op.create_table(
        "trans_user_flags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.String(length=27), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("user_id", "transaction_id", "type", name="_user_transaction_uc"),
    )
    op.create_table(
        "trans_tag_values",
        sa.Column("transaction_id", sa.String(length=27), nullable=False),
        sa.Column("value_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["value_id"], ["tag_values.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transaction_id", "value_id"),
    )


def downgrade() -> None:
    op.drop_table("trans_tag_values")
    op.drop_table("trans_user_flags")
    op.drop_table("tag_values")
    op.drop_table("metric_values")
    op.drop_table("messages")
    op.drop_table("users")
    op.drop_index(op.f("ix_transactions_x_status_class"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_x_method"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_type"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_started_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_endpoint"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("tags")
    op.drop_table("metrics")
    op.drop_table("blobs")
