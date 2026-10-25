"""cache records

Revision ID: 7b2e5d9a1c40
Revises:
Create Date: 2026-10-25 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b2e5d9a1c40"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("http_cache",)
depends_on: Union[str, Sequence[str], None] = None

KEY = sa.Text().with_variant(sa.Text(collation="C"), "postgresql")


def upgrade() -> None:
    op.create_table(
        "http_cache_resources",
        sa.Column("key", KEY, nullable=False),
        sa.Column("endpoint", KEY, nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_http_cache_resources")),
    )
    op.create_index("ix_http_cache_resources_endpoint_key", "http_cache_resources", ["endpoint", "key"], unique=False)
    op.create_table(
        "http_cache_bodies",
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("digest", name=op.f("pk_http_cache_bodies")),
    )
    op.create_table(
        "http_cache_variants",
        sa.Column("key", KEY, nullable=False),
        sa.Column("variant", sa.String(length=64), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("stamp", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("vary", sa.Text(), nullable=True),
        sa.Column("body_digest", sa.String(length=64), nullable=False),
        sa.Column("body_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("stored_at", sa.Float(), nullable=False),
        sa.Column("head", sa.LargeBinary(), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["body_digest"],
            ["http_cache_bodies.digest"],
            name=op.f("fk_http_cache_variants_body_digest_http_cache_bodies"),
        ),
        sa.ForeignKeyConstraint(
            ["key"],
            ["http_cache_resources.key"],
            name=op.f("fk_http_cache_variants_key_http_cache_resources"),
        ),
        sa.PrimaryKeyConstraint("key", "variant", name=op.f("pk_http_cache_variants")),
        sa.UniqueConstraint("entry_id", name=op.f("uq_http_cache_variants_entry_id")),
    )
    op.create_index("ix_http_cache_variants_stored_at", "http_cache_variants", ["stored_at"], unique=False)
    op.create_index("ix_http_cache_variants_body_digest", "http_cache_variants", ["body_digest"], unique=False)
    op.create_index(
        "ix_http_cache_variants_endpoint_body_size", "http_cache_variants", ["endpoint", "body_size"], unique=False
    )
    op.create_table(
        "http_cache_stats",
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("entries", sa.BigInteger(), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("refused", sa.BigInteger(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("endpoint", name=op.f("pk_http_cache_stats")),
    )


def downgrade() -> None:
    op.drop_table("http_cache_stats")
    op.drop_index("ix_http_cache_variants_endpoint_body_size", table_name="http_cache_variants")
    op.drop_index("ix_http_cache_variants_body_digest", table_name="http_cache_variants")
    op.drop_index("ix_http_cache_variants_stored_at", table_name="http_cache_variants")
    op.drop_table("http_cache_variants")
    op.drop_table("http_cache_bodies")
    op.drop_index("ix_http_cache_resources_endpoint_key", table_name="http_cache_resources")
    op.drop_table("http_cache_resources")
