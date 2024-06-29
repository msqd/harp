from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import partial

import pytest
from alembic import command
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.redis import AsyncRedisContainer
from whistle import AsyncEventDispatcher

from harp.models import Blob, Message, Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp_apps.sqlalchemy_storage.storages.sql import SqlStorage
from harp_apps.sqlalchemy_storage.types import IBlobStorage
from harp_apps.sqlalchemy_storage.utils.migrations import create_alembic_config, do_migrate


@asynccontextmanager
async def get_scoped_database_url(database_url, test_id):
    """
    Returns a "scoped" database URL that is unique to the test_id, with a database available to run some tests. Logic
    differs a bit depending on the target dialect, but the idea is to create a new database for each test, and drop it
    afterward. For sqlite, we bypass this as the "migration" process is a simple reset+recreate all.

    :param database_url:
    :param test_id:
    :return:
    """
    admin_url = make_url(database_url)
    dialect = admin_url.get_dialect().name

    if dialect == "mysql":
        admin_url = admin_url.set(username="root")

    admin_engine = create_async_engine(admin_url.render_as_string(hide_password=False))

    if dialect == "sqlite":
        try:
            yield database_url
        finally:
            await admin_engine.dispose()

    elif dialect in ("mysql", "postgresql"):
        db_name = f"test_{test_id}"
        url = make_url(database_url).set(database=db_name)

        async with admin_engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")

            await conn.execute(text(f"CREATE DATABASE {url.database}"))
            if dialect == "mysql":
                await conn.execute(text(f"GRANT ALL PRIVILEGES ON {url.database}.* TO '{url.username}'@'%'"))

        try:
            yield url.render_as_string(hide_password=False)
        finally:
            async with admin_engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                await conn.execute(text(f"DROP DATABASE {url.database}"))
            await admin_engine.dispose()

    else:
        raise RuntimeError(f"Unsupported dialect «{admin_engine.dialect.name}»")


DEFAULT_STORAGE_SETTINGS = {
    "url": "sqlite+aiosqlite:///:memory:",
    "migrate": False,
}


class SqlalchemyStorageTestFixtureMixin:
    @pytest.fixture
    async def sql_engine(self, database_url, test_id) -> AsyncEngine:
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
    def storage_settings(self, sql_engine) -> SqlAlchemyStorageSettings:
        return SqlAlchemyStorageSettings(**(DEFAULT_STORAGE_SETTINGS | {"url": sql_engine.url}))

    @pytest.fixture
    async def blob_storage(self, blob_storage_type, sql_engine, storage_settings) -> IBlobStorage:
        if blob_storage_type == "sql":
            from harp_apps.sqlalchemy_storage.storages.blobs.sql import SqlBlobStorage

            yield SqlBlobStorage(sql_engine)
        elif blob_storage_type == "redis":
            with AsyncRedisContainer() as redis_container:
                from harp_apps.sqlalchemy_storage.storages.blobs.redis import RedisBlobStorage

                yield RedisBlobStorage(await redis_container.get_async_client())
        else:
            raise ValueError(f"Unsupported blob storage type: {blob_storage_type}")

    @pytest.fixture
    async def storage(self, sql_engine, blob_storage, storage_settings) -> SqlStorage:
        storage = SqlStorage(
            sql_engine,
            dispatcher=AsyncEventDispatcher(),
            blob_storage=blob_storage,
            settings=storage_settings,
        )
        # migrations are disabled because already done by the sql_engine fixture, but we still need to do additional
        # initialization steps.
        await storage.initialize()
        yield storage

    async def create_transaction(self, storage: SqlStorage, **kwargs):
        return await storage.transactions.create(
            Transaction(
                **{
                    **{
                        "id": generate_transaction_id_ksuid(),
                        "type": "http",
                        "endpoint": "/",
                        "started_at": datetime.now(UTC),
                    },
                    **kwargs,
                }
            )
        )

    async def create_blob(self, blob_storage: IBlobStorage, data, /, **kwargs):
        return await blob_storage.put(Blob.from_data(data, **kwargs))

    async def create_message(self, storage: SqlStorage, **kwargs):
        return await storage.messages.create(Message(**kwargs))
