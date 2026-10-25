from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from harp_apps.audit.models import AuditEvent
from harp_apps.storage.utils.migrations import create_alembic_config, discover_migration_locations, table_belongs_to


def test_audit_owns_a_branch_of_its_own():
    assert "audit" in discover_migration_locations()

    script = ScriptDirectory.from_config(create_alembic_config("sqlite+aiosqlite:///:memory:"))

    assert script.get_revision("audit").down_revision is None
    assert len(script.get_heads()) == 2  # storage and audit


def test_audit_tables_are_prefixed_and_belong_to_audit():
    assert AuditEvent.__tablename__ == "audit_events"
    assert table_belongs_to("audit", AuditEvent.__tablename__, ["audit", "storage"])
    assert not table_belongs_to("storage", AuditEvent.__tablename__, ["audit", "storage"])


async def test_the_migration_matches_the_model(sql_engine):
    if sql_engine.dialect.name == "sqlite":
        return  # sqlite never runs alembic, its schema is created from the models

    def ours(obj, name, type_, *_):
        return (name if type_ == "table" else obj.table.name).startswith("audit_")

    def differences(sync_conn):
        context = MigrationContext.configure(sync_conn, opts={"include_object": ours})
        return compare_metadata(context, AuditEvent.metadata)

    async with sql_engine.connect() as connection:
        assert await connection.run_sync(differences) == []
