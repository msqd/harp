"""widen blob id for cache keys

``blobs.id`` was sized for a sha1 hexdigest (40 characters), which is what message blobs use. HTTP
cache entries are keyed by hishel, which uses a sha256 hexdigest (64 characters), and both land in
the same column. PostgreSQL and MySQL enforce the declared width and rejected every cache write.

Widening is backward compatible: existing 32 and 40 character identifiers are unaffected, no value
is rewritten, and the primary key and unique constraint are preserved.

SQLite never reaches this migration. ``harp_apps/storage/utils/migrations.py`` takes a
``Base.metadata.create_all`` branch for that dialect, so new SQLite databases get the current width
directly and existing files need no change, since SQLite does not enforce ``VARCHAR`` length at all.

Revision ID: a1c7f3b52e04
Revises: 29d104241dae
Create Date: 2026-08-16 07:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c7f3b52e04"
down_revision: Union[str, None] = "29d104241dae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "blobs",
        "id",
        existing_type=sa.VARCHAR(length=40),
        type_=sa.VARCHAR(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Narrowing truncates any cache entry key stored while the column was wide, so anything longer
    # than the old width has to go before the type can be changed back.
    op.execute("DELETE FROM blobs WHERE length(id) > 40")
    op.alter_column(
        "blobs",
        "id",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.VARCHAR(length=40),
        existing_nullable=False,
    )
