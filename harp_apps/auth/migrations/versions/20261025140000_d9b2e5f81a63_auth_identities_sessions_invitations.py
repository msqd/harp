"""identities, sessions and invitations

Creates ``auth_identities`` (the link between an account and a sign-in method), ``auth_sessions`` (server-side
sessions, the cookie holds a secret of which only the hash is kept) and ``auth_invitations`` (single-use offers of an
account with a role; here only the setup link, which nobody offered, uses it).

Only PostgreSQL is migrated: SQLite is never migrated by alembic (``create_all``) and MySQL and MariaDB are unsupported
(ADR-0005), so the revision logs a warning and does nothing there.

Revision ID: d9b2e5f81a63
Revises: b3f6a1d94c27
Create Date: 2026-10-25 14:00:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9b2e5f81a63"
down_revision: Union[str, None] = "b3f6a1d94c27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def _is_postgresql() -> bool:
    if op.get_bind().dialect.name == "postgresql":
        return True
    logger.warning("Identities, sessions and invitations are only migrated on PostgreSQL.")
    return False


def _timestamp(name: str, *, nullable: bool = True, default_now: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.TIMESTAMP(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if default_now else None,
    )


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("password_version", sa.Integer(), nullable=False, server_default="0"),
        _timestamp("created_at", nullable=False, default_now=True),
        _timestamp("last_sign_in_at"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["auth_accounts.id"],
            name=op.f("fk_auth_identities_account_id_auth_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_identities")),
        sa.UniqueConstraint("method", "issuer", "subject", name=op.f("uq_auth_identities_method_issuer_subject")),
    )
    op.create_index(op.f("ix_auth_identities_account_id"), "auth_identities", ["account_id"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False, server_default="0"),
        _timestamp("created_at", nullable=False, default_now=True),
        _timestamp("last_seen_at", nullable=False, default_now=True),
        _timestamp("expires_at", nullable=False),
        _timestamp("revoked_at"),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["auth_accounts.id"],
            name=op.f("fk_auth_sessions_account_id_auth_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["auth_identities.id"],
            name=op.f("fk_auth_sessions_identity_id_auth_identities"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("secret_hash", name=op.f("uq_auth_sessions_secret_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_account_id"), "auth_sessions", ["account_id"])

    op.create_table(
        "auth_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("expected_email", sa.String(320), nullable=True),
        sa.Column("invited_by", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        _timestamp("created_at", nullable=False, default_now=True),
        _timestamp("expires_at", nullable=False),
        _timestamp("accepted_at"),
        _timestamp("revoked_at"),
        sa.CheckConstraint("role IN ('viewer', 'editor', 'admin')", name=op.f("ck_auth_invitations_role")),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["auth_accounts.id"],
            name=op.f("fk_auth_invitations_invited_by_auth_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["auth_accounts.id"],
            name=op.f("fk_auth_invitations_account_id_auth_accounts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_invitations")),
        sa.UniqueConstraint("secret_hash", name=op.f("uq_auth_invitations_secret_hash")),
    )


def downgrade() -> None:
    if not _is_postgresql():
        return

    op.drop_table("auth_invitations")
    op.drop_index(op.f("ix_auth_sessions_account_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index(op.f("ix_auth_identities_account_id"), table_name="auth_identities")
    op.drop_table("auth_identities")
