"""persist transaction markers

Adds a nullable ``transactions.markers`` text column holding the markers of a transaction (rule
``skip-*``, ``shed-*`` and ``truncated-*``) as a sorted, comma separated list. Existing rows get
``NULL``, read back as no marker.

SQLite never reaches this migration: ``harp_apps/storage/utils/migrations.py`` takes a
``Base.metadata.create_all`` branch for that dialect.

Revision ID: c5e8b2d41f73
Revises: a1c7f3b52e04
Create Date: 2026-10-17 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5e8b2d41f73"
down_revision: Union[str, None] = "a1c7f3b52e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("markers", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "markers")
