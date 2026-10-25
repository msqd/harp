"""take users over as auth_accounts

Renames ``users`` to ``auth_accounts`` and gives it what an account needs: ``display_name``, ``email`` (unique, lower
case), ``kind``, ``role``, ``created_at``, ``last_seen_at`` and ``disabled_at``. ``username`` goes from 32 to 255
characters. Favourites (``trans_user_flags``) keep their foreign key and so their author.

Rows that exist are accounts that may no longer be configured, so none gets access from here: they become disabled
``viewer`` people, and the one-time import of the users configured for Basic enables them as Admin. ``anonymous``
authors favourites recorded before there were accounts and never signs in: it becomes a ``system`` account.

A downgrade gives ``users`` back; it fails if a username is longer than 32 characters, and the accounts created since
(machines, system) become users like the others.

Only PostgreSQL is migrated: SQLite is never migrated by alembic (``harp_apps/storage/utils/migrations.py`` runs
``create_all``, an existing file is recreated on upgrade), and MySQL and MariaDB are unsupported (ADR-0005), so the
revision logs a warning and does nothing there.

Revision ID: b3f6a1d94c27
Revises:
Create Date: 2026-10-25 12:00:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f6a1d94c27"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("auth",)
# the naming convention revision of the storage branch: the constraint names renamed below are the ones it gave
depends_on: Union[str, Sequence[str], None] = "e7a4d9c26b18"

logger = logging.getLogger("alembic.runtime.migration")

# (table, name before, name after): "users" stands for the accounts table, whatever it is called at that time
RENAMED_CONSTRAINTS = (
    ("users", "pk_users", "pk_auth_accounts"),
    ("users", "uq_users_id", "uq_auth_accounts_id"),
    ("users", "uq_users_username", "uq_auth_accounts_username"),
    ("trans_user_flags", "fk_trans_user_flags_user_id_users", "fk_trans_user_flags_user_id_auth_accounts"),
)

CHECKS = {
    "ck_auth_accounts_email_lowercase": "email = lower(email)",
    "ck_auth_accounts_kind": "kind IN ('person', 'machine', 'system')",
    "ck_auth_accounts_role": "role IN ('viewer', 'editor', 'admin')",
}


def _is_postgresql() -> bool:
    if op.get_bind().dialect.name == "postgresql":
        return True
    logger.warning("Accounts are only migrated on PostgreSQL: users are left as they are.")
    return False


def _rename_constraints(*, upgrading: bool) -> None:
    for table, old, new in RENAMED_CONSTRAINTS:
        old, new = (old, new) if upgrading else (new, old)
        # always run while the table is named auth_accounts: after the rename going up, before it going down
        table = "auth_accounts" if table == "users" else table
        op.execute(sa.text(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}"'))


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.rename_table("users", "auth_accounts")
    op.execute(sa.text("ALTER SEQUENCE IF EXISTS users_id_seq RENAME TO auth_accounts_id_seq"))
    _rename_constraints(upgrading=True)

    op.alter_column("auth_accounts", "username", existing_type=sa.String(32), type_=sa.String(255))
    op.add_column("auth_accounts", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("auth_accounts", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("auth_accounts", sa.Column("kind", sa.String(16), nullable=False, server_default="person"))
    op.add_column("auth_accounts", sa.Column("role", sa.String(16), nullable=False, server_default="viewer"))
    op.add_column(
        "auth_accounts",
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("auth_accounts", sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("auth_accounts", sa.Column("disabled_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("auth_accounts", sa.Column("disabled_reason", sa.String(32), nullable=True))

    # nobody gets access from a migration: the accounts that existed are disabled viewers until the one-time import of
    # the users configured for Basic enables them (as Admin). ``anonymous`` authors favourites and never signs in.
    op.execute(sa.text("UPDATE auth_accounts SET kind = 'system' WHERE username = 'anonymous'"))
    # marked, so the import enables these and only these: what the Operator decides meanwhile is never overwritten
    op.execute(
        sa.text(
            "UPDATE auth_accounts SET disabled_at = now(), disabled_reason = 'migrated' WHERE username <> 'anonymous'"
        )
    )

    # the defaults served the rows that existed, new accounts say what they are
    op.alter_column("auth_accounts", "kind", server_default=None)
    op.alter_column("auth_accounts", "role", server_default=None)

    op.create_unique_constraint(op.f("uq_auth_accounts_email"), "auth_accounts", ["email"])
    for name, condition in CHECKS.items():
        op.create_check_constraint(op.f(name), "auth_accounts", condition)


def downgrade() -> None:
    if not _is_postgresql():
        return

    for name in CHECKS:
        op.drop_constraint(op.f(name), "auth_accounts", type_="check")
    op.drop_constraint("uq_auth_accounts_email", "auth_accounts", type_="unique")
    for column in (
        "disabled_reason",
        "disabled_at",
        "last_seen_at",
        "created_at",
        "role",
        "kind",
        "email",
        "display_name",
    ):
        op.drop_column("auth_accounts", column)
    op.alter_column("auth_accounts", "username", existing_type=sa.String(255), type_=sa.String(32))

    _rename_constraints(upgrading=False)
    op.execute(sa.text("ALTER SEQUENCE IF EXISTS auth_accounts_id_seq RENAME TO users_id_seq"))
    op.rename_table("auth_accounts", "users")
