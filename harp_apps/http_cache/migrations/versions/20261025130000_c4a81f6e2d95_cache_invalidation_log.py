"""cache invalidation log

Revision ID: c4a81f6e2d95
Revises: 7b2e5d9a1c40
Create Date: 2026-10-25 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a81f6e2d95"
down_revision: Union[str, None] = "7b2e5d9a1c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KEY = sa.Text().with_variant(sa.Text(collation="C"), "postgresql")


def upgrade() -> None:
    op.create_table(
        "http_cache_bans",
        sa.Column("seq", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("prefix", KEY, nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("seq", name=op.f("pk_http_cache_bans")),
    )
    op.create_index("ix_http_cache_bans_prefix_seq", "http_cache_bans", ["prefix", "seq"], unique=False)
    op.create_table(
        "http_cache_counter",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_http_cache_counter")),
    )


def downgrade() -> None:
    op.drop_table("http_cache_counter")
    op.drop_index("ix_http_cache_bans_prefix_seq", table_name="http_cache_bans")
    op.drop_table("http_cache_bans")
