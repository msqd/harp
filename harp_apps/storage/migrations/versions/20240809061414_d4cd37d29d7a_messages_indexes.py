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


def _create_unique_id(table: str) -> None:
    """
    Create the unique constraint on ``id`` that the initial revision already created.

    Unnamed, the database tolerates the duplicate. Once ``Base.metadata`` carries a naming convention, alembic gives
    both the same name and the second one would fail, so it is skipped then.
    """
    context = op.get_context()
    convention = getattr(context.opts.get("target_metadata"), "naming_convention", None) or {}
    uniques = sa.inspect(op.get_bind()).get_unique_constraints(table)
    if "uq" in convention and any(unique["column_names"] == ["id"] for unique in uniques):
        return
    op.create_unique_constraint(None, table, ["id"])


def upgrade() -> None:
    _create_unique_id("blobs")
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
    _create_unique_id("messages")
    _create_unique_id("metrics")
    op.create_unique_constraint("__values_uc", "tag_values", ["tag_id", "value"])
    _create_unique_id("tag_values")
    _create_unique_id("tags")
    _create_unique_id("trans_user_flags")
    op.alter_column("transactions", "type", existing_type=sa.VARCHAR(length=10), nullable=False)
    op.alter_column(
        "transactions",
        "started_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )
    _create_unique_id("transactions")
    _create_unique_id("users")


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
