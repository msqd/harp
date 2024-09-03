"""messages indexes

Revision ID: d4cd37d29d7a
Revises: 0b4d9cb71c38
Create Date: 2024-08-09 06:14:14.691024

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4cd37d29d7a"
down_revision: Union[str, None] = "0b4d9cb71c38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(None, "blobs", ["id"])
    op.alter_column("messages", "kind", existing_type=sa.VARCHAR(length=10), nullable=False)
    op.alter_column("messages", "summary", existing_type=sa.VARCHAR(length=255), nullable=False)
    op.alter_column("messages", "headers", existing_type=sa.VARCHAR(length=40), nullable=False)
    op.alter_column(
        "messages",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )
    op.alter_column(
        "messages",
        "transaction_id",
        existing_type=sa.VARCHAR(length=27),
        nullable=False,
    )
    op.create_index("ix_transaction_id", "messages", ["transaction_id"], unique=False)
    op.create_unique_constraint(None, "messages", ["id"])
    op.create_unique_constraint(None, "metrics", ["id"])
    op.create_unique_constraint("__values_uc", "tag_values", ["tag_id", "value"])
    op.create_unique_constraint(None, "tag_values", ["id"])
    op.create_unique_constraint(None, "tags", ["id"])
    op.create_unique_constraint(None, "trans_user_flags", ["id"])
    op.alter_column("transactions", "type", existing_type=sa.VARCHAR(length=10), nullable=False)
    op.alter_column(
        "transactions",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )
    op.create_unique_constraint(None, "transactions", ["id"])
    op.create_unique_constraint(None, "users", ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "users", type_="unique")
    op.drop_constraint(None, "transactions", type_="unique")
    op.alter_column(
        "transactions",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column("transactions", "type", existing_type=sa.VARCHAR(length=10), nullable=True)
    op.drop_constraint(None, "trans_user_flags", type_="unique")
    op.drop_constraint(None, "tags", type_="unique")
    op.drop_constraint(None, "tag_values", type_="unique")
    op.drop_constraint("__values_uc", "tag_values", type_="unique")
    op.drop_constraint(None, "metrics", type_="unique")
    op.drop_constraint(None, "messages", type_="unique")
    op.drop_index("ix_transaction_id", table_name="messages")
    op.alter_column("messages", "transaction_id", existing_type=sa.VARCHAR(length=27), nullable=True)
    op.alter_column(
        "messages",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column("messages", "headers", existing_type=sa.VARCHAR(length=40), nullable=True)
    op.alter_column("messages", "summary", existing_type=sa.VARCHAR(length=255), nullable=True)
    op.alter_column("messages", "kind", existing_type=sa.VARCHAR(length=10), nullable=True)
    op.drop_constraint(None, "blobs", type_="unique")
