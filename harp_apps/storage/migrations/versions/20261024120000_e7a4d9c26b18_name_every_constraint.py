"""name every constraint

Gives every primary key, unique constraint and foreign key the name the naming convention of
``Base.metadata`` produces, and renames ``ix_transaction_id`` to ``ix_messages_transaction_id``.
Until now they carried the names their database generated, or none on SQLite, which alembic batch
migrations cannot alter.

Migrations 248285939c4c and d4cd37d29d7a stacked duplicates of the same unique constraint
(``users.id`` twice, ``tag_values.(tag_id, value)`` twice...) on PostgreSQL and MySQL, which a
convention could not name apart. One of each is kept. A downgrade restores the generated names
but does not bring the duplicates back.

The names are computed here and frozen, so that a later change of the convention does not rewrite
this revision. MySQL names no primary key, its are left alone.

SQLite never reaches this migration at boot: ``harp_apps/storage/utils/migrations.py`` takes a
``Base.metadata.create_all`` branch for that dialect. It is still written for it, as batch
migrations are what this revision unblocks.

Revision ID: e7a4d9c26b18
Revises: c5e8b2d41f73
Create Date: 2026-10-24 12:00:00.000000

"""

from dataclasses import dataclass
from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a4d9c26b18"
down_revision: Union[str, None] = "c5e8b2d41f73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "blobs",
    "messages",
    "metric_values",
    "metrics",
    "tag_values",
    "tags",
    "trans_tag_values",
    "trans_user_flags",
    "transactions",
    "users",
)

# names that were given explicitly, before the convention
EXPLICIT_UNIQUES = {
    ("tag_values", ("tag_id", "value")): {"sqlite": "__values_uc", "default": "_tag_values_uc"},
    ("trans_user_flags", ("user_id", "transaction_id", "type")): {"default": "_user_transaction_uc"},
}
RENAMED_INDEXES = {("messages", "ix_transaction_id"): "ix_messages_transaction_id"}


@dataclass
class Constraint:
    table: str
    kind: str  # pk, uq, fk
    columns: tuple
    old: Optional[str]
    new: Optional[str]
    referred_table: Optional[str] = None
    referred_columns: tuple = ()
    ondelete: Optional[str] = None


def _convention_name(table, kind, columns, referred_table):
    columns = "_".join(columns)
    return {
        "pk": f"pk_{table}",
        "uq": f"uq_{table}_{columns}",
        "fk": f"fk_{table}_{columns}_{referred_table}",
    }[kind]


def _generated_name(dialect, table, kind, columns, referred_table):
    """The name a database gives, or ``None`` where it leaves the constraint unnamed or the name is not ours to set."""
    explicit = EXPLICIT_UNIQUES.get((table, columns)) if kind == "uq" else None
    if explicit:
        return explicit.get(dialect, explicit["default"])
    if dialect == "postgresql":
        return {"pk": f"{table}_pkey", "uq": f"{table}_{'_'.join(columns)}_key", "fk": f"{table}_{columns[0]}_fkey"}[
            kind
        ]
    if dialect == "mysql" and kind == "uq":
        return columns[0]
    return None


def _constraints(bind, *, upgrading):
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name
    existing_tables = set(inspector.get_table_names())
    for table in TABLES:
        if table not in existing_tables:
            continue

        def new_name(kind, columns, referred_table=None):
            if upgrading:
                return _convention_name(table, kind, columns, referred_table)
            return _generated_name(dialect, table, kind, columns, referred_table)

        pk = inspector.get_pk_constraint(table)
        if dialect != "mysql" and pk["constrained_columns"]:
            columns = tuple(pk["constrained_columns"])
            yield Constraint(table, "pk", columns, pk["name"], new_name("pk", columns))

        kept = {}
        for unique in sorted(inspector.get_unique_constraints(table), key=lambda u: u["name"] or ""):
            columns = tuple(unique["column_names"])
            if columns in kept:
                if upgrading:
                    op.drop_constraint(unique["name"], table, type_="unique")
                continue
            kept[columns] = unique
            yield Constraint(table, "uq", columns, unique["name"], new_name("uq", columns))

        for fk in sorted(inspector.get_foreign_keys(table), key=lambda f: f["constrained_columns"]):
            columns = tuple(fk["constrained_columns"])
            yield Constraint(
                table,
                "fk",
                columns,
                fk["name"],
                new_name("fk", columns, fk["referred_table"]),
                fk["referred_table"],
                tuple(fk["referred_columns"]),
                fk["options"].get("ondelete"),
            )


def _renamed_indexes(*, upgrading):
    for (table, old), new in RENAMED_INDEXES.items():
        yield (table, old, new) if upgrading else (table, new, old)


def _rename_postgresql(constraints, indexes):
    for c in constraints:
        if c.old != c.new:
            op.execute(sa.text(f'ALTER TABLE "{c.table}" RENAME CONSTRAINT "{c.old}" TO "{c.new}"'))
    for _, old, new in indexes:
        op.execute(sa.text(f'ALTER INDEX "{old}" RENAME TO "{new}"'))


def _rename_mysql(constraints, indexes):
    for c in constraints:
        if c.kind == "uq" and c.old != c.new:
            op.execute(sa.text(f"ALTER TABLE `{c.table}` RENAME INDEX `{c.old}` TO `{c.new}`"))
    for c in constraints:
        if c.kind == "fk":
            op.drop_constraint(c.old, c.table, type_="foreignkey")
    for c in constraints:
        if c.kind == "fk":
            op.create_foreign_key(
                c.new, c.table, c.referred_table, list(c.columns), list(c.referred_columns), ondelete=c.ondelete
            )
    for table, old, new in indexes:
        op.execute(sa.text(f"ALTER TABLE `{table}` RENAME INDEX `{old}` TO `{new}`"))


def _rename_sqlite(bind, constraints, indexes):
    """SQLite cannot rename a constraint: recreate each table from its reflection, constraints renamed."""
    for table in dict.fromkeys(c.table for c in constraints):
        reflected = sa.Table(table, sa.MetaData(), autoload_with=bind)
        by_key = {(c.kind, c.columns): c.new for c in constraints if c.table == table}
        for constraint in reflected.constraints:
            columns = tuple(column.name for column in constraint.columns)
            if isinstance(constraint, sa.PrimaryKeyConstraint):
                constraint.name = by_key[("pk", columns)]
            elif isinstance(constraint, sa.UniqueConstraint):
                constraint.name = by_key[("uq", columns)]
            elif isinstance(constraint, sa.ForeignKeyConstraint):
                constraint.name = by_key[("fk", columns)]
        for index in reflected.indexes:
            for index_table, old, new in indexes:
                if index_table == table and index.name == old:
                    index.name = new
        with op.batch_alter_table(table, copy_from=reflected, recreate="always"):
            pass


def _apply(*, upgrading):
    bind = op.get_bind()
    constraints = list(_constraints(bind, upgrading=upgrading))
    indexes = list(_renamed_indexes(upgrading=upgrading))
    if bind.dialect.name == "postgresql":
        _rename_postgresql(constraints, indexes)
    elif bind.dialect.name == "mysql":
        _rename_mysql(constraints, indexes)
    else:
        _rename_sqlite(bind, constraints, indexes)


def upgrade() -> None:
    _apply(upgrading=True)


def downgrade() -> None:
    _apply(upgrading=False)
