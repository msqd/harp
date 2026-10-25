from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from harp_apps.http_cache.models import CacheBan, CacheBody, CacheCounter, CacheResource, CacheStats, CacheVariant
from harp_apps.storage.utils.migrations import create_alembic_config, discover_migration_locations, table_belongs_to

TABLES = (CacheResource, CacheBody, CacheVariant, CacheStats, CacheBan, CacheCounter)


def test_the_cache_owns_a_branch_of_its_own():
    assert "http_cache" in discover_migration_locations()

    script = ScriptDirectory.from_config(create_alembic_config("sqlite+aiosqlite:///:memory:"))

    assert script.get_revision("http_cache").down_revision is None


def test_cache_tables_are_prefixed_and_belong_to_the_cache():
    applications = ["http_cache", "storage"]

    for table in TABLES:
        assert table.__tablename__.startswith("http_cache_")
        assert table_belongs_to("http_cache", table.__tablename__, applications)
        assert not table_belongs_to("storage", table.__tablename__, applications)


async def test_keys_are_compared_bytewise_on_postgresql(sql_engine):
    if sql_engine.dialect.name != "postgresql":
        return  # sqlite compares text bytewise by default

    async with sql_engine.connect() as connection:
        bytewise = (
            await connection.execute(
                text(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE collation_name = 'C' AND table_name LIKE 'http_cache_%'"
                )
            )
        ).all()

    assert sorted(bytewise) == [
        ("http_cache_bans", "prefix"),
        ("http_cache_resources", "endpoint"),
        ("http_cache_resources", "key"),
        ("http_cache_variants", "key"),
    ]


async def test_the_migration_matches_the_model(sql_engine):
    if sql_engine.dialect.name == "sqlite":
        return  # sqlite never runs alembic, its schema is created from the models

    def ours(obj, name, type_, *_):
        return (name if type_ == "table" else obj.table.name).startswith("http_cache_")

    def differences(sync_conn):
        context = MigrationContext.configure(sync_conn, opts={"include_object": ours})
        return compare_metadata(context, CacheVariant.metadata)

    async with sql_engine.connect() as connection:
        assert await connection.run_sync(differences) == []
