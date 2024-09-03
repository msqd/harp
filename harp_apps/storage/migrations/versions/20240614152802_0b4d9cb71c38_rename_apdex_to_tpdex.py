"""rename apdex to tpdex

Revision ID: 0b4d9cb71c38
Revises: 248285939c4c
Create Date: 2024-06-14 15:28:02.344136

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0b4d9cb71c38"
down_revision: Union[str, None] = "248285939c4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "transactions",
        "apdex",
        new_column_name="tpdex",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "transactions",
        "tpdex",
        new_column_name="apdex",
        existing_type=sa.Integer(),
        nullable=True,
    )
