"""persist the cache outcome of transactions

Adds nullable ``transactions.x_cache_*`` columns: the outcome of the cache for the transaction (hit, stale, revalidated,
miss, uncacheable), the cache key (the endpoint and path in clear, then a hash of the query, never a query value), the
variant, the invalidation number the response is valid as of, its age and its remaining freshness. The outcome is
indexed, for the transaction list filter. Existing rows get ``NULL``, read back as an outcome the cache did not report.

SQLite never reaches this migration: ``harp_apps/storage/utils/migrations.py`` takes a
``Base.metadata.create_all`` branch for that dialect.

Revision ID: 9d3f6a21b8c7
Revises: e7a4d9c26b18
Create Date: 2026-10-25 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d3f6a21b8c7"
down_revision: Union[str, None] = "e7a4d9c26b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("x_cache_outcome", sa.String(length=16), nullable=True))
    op.add_column("transactions", sa.Column("x_cache_key", sa.Text(), nullable=True))
    op.add_column("transactions", sa.Column("x_cache_variant", sa.String(length=64), nullable=True))
    op.add_column("transactions", sa.Column("x_cache_seq", sa.BigInteger(), nullable=True))
    op.add_column("transactions", sa.Column("x_cache_age", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("x_cache_ttl", sa.Integer(), nullable=True))
    op.create_index("ix_transactions_x_cache_outcome", "transactions", ["x_cache_outcome"])


def downgrade() -> None:
    op.drop_index("ix_transactions_x_cache_outcome", table_name="transactions")
    for column in ("x_cache_ttl", "x_cache_age", "x_cache_seq", "x_cache_variant", "x_cache_key", "x_cache_outcome"):
        op.drop_column("transactions", column)
