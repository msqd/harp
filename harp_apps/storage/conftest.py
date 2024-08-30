from functools import partial

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from conftest import DEFAULT_STORAGE_SETTINGS
from harp.utils.testing.databases import TEST_DATABASES
from harp_apps.storage.services import SqlStorage

from .services.blob_storages.redis import RedisBlobStorage
from .settings import StorageSettings
from .utils.migrations import create_alembic_config, do_migrate
from .utils.testing.redis import create_redis_client
from .utils.testing.sql import create_database_container_for, get_scoped_database_url


@pytest.fixture
async def redis_blob_storage():
    async with create_redis_client() as async_client:
        from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage

        yield RedisBlobStorage(async_client)


@pytest.fixture
async def sql_blob_storage(sql_engine):
    from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage

    yield SqlBlobStorage(sql_engine)


@pytest.fixture(params=["sql", "redis"])
async def blob_storage(request, sql_engine):
    if request.param == "sql":
        from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage

        yield SqlBlobStorage(sql_engine)
    elif request.param == "redis":
        async with create_redis_client() as async_client:
            yield RedisBlobStorage(async_client)

    else:
        raise ValueError(f"Unsupported blob storage type: {request.param}")


@pytest.fixture(scope="session", params=TEST_DATABASES)
def database_url(request):
    dialect, image, driver = request.param.split("|")
    yield from create_database_container_for(dialect, image, driver)


@pytest.fixture
async def sql_engine(database_url, test_id) -> AsyncEngine:
    """
    Use a DMBS conncetion string to create a sqlalchemy async engine to a new isolated database that will gets an
    initial status/structure/schema by executing migrations on it, whatever the migration process is for the given
    URL (for example, sqlite will use a simple create_all strategy, while postgres or mysql will use alembic).

    This looks a bit overkill, but this is the simplest way to guarantee isolated and repeatable tests that depends on
    databases.

    The isolated database name will be based on the test_id fixture value, which will create an unique hash string for
    each test.

    """
    async with get_scoped_database_url(database_url, test_id) as scoped_database_url:
        engine = create_async_engine(scoped_database_url)
        try:
            # todo refactor (dup in sqlstorage.initialize / sqlstorage._run_migrations)
            alembic_cfg = create_alembic_config(engine.url.render_as_string(hide_password=False))
            migrator = partial(command.upgrade, alembic_cfg, "head")
            await do_migrate(engine, migrator=migrator)
            yield engine
        finally:
            await engine.dispose()


@pytest.fixture
async def sql_storage(sql_engine, blob_storage) -> SqlStorage:
    storage = SqlStorage(
        sql_engine,
        blob_storage=blob_storage,
        settings=StorageSettings(**(DEFAULT_STORAGE_SETTINGS | {"url": sql_engine.url})),
    )
    # migrations are disabled because already done by the sql_engine fixture, but we still need to do additional
    # initialization steps.
    await storage.initialize()
    yield storage
