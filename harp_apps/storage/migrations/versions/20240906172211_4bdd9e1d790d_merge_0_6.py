"""merge 0.6

Revision ID: 4bdd9e1d790d
Revises:
Create Date: 2024-09-06 17:22:11.824809

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4bdd9e1d790d"
down_revision = ("d4cd37d29d7a", "4ab341a710f4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "messages", "summary", existing_type=sa.VARCHAR(length=255), type_=sa.Text(), existing_nullable=True
    )


def downgrade() -> None:
    pass
