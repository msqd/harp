from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine
from whistle import AsyncEventDispatcher

from harp.models import Blob, Message, Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp_apps.sqlalchemy_storage.storage import SqlAlchemyStorage


async def _create_storage(*, settings, dispatcher=None) -> SqlAlchemyStorage:
    storage = SqlAlchemyStorage(
        dispatcher=dispatcher or AsyncEventDispatcher(),
        settings=SqlAlchemyStorageSettings(**settings),
    )
    await storage.initialize()

    return storage


@asynccontextmanager
async def get_scoped_database_url(database_url, test_id):
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


class SqlalchemyStorageTestFixtureMixin:
    storage_settings = {
        "url": "sqlite+aiosqlite:///:memory:",
    }

    def get_sqlalchemy_storage_settings(self, settings):
        return {**self.storage_settings, **settings}

    @pytest.fixture
    async def storage(self, database_url, test_id) -> SqlAlchemyStorage:
        async with get_scoped_database_url(database_url, test_id) as scoped_database_url:
            storage = await _create_storage(
                settings=self.get_sqlalchemy_storage_settings({"url": scoped_database_url}),
            )
            try:
                yield storage
            finally:
                await storage.engine.dispose()

    async def create_transaction(self, storage: SqlAlchemyStorage, **kwargs):
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

    async def create_blob(self, storage: SqlAlchemyStorage, data, /, **kwargs):
        return await storage.blobs.create(Blob.from_data(data, **kwargs))

    async def create_message(self, storage: SqlAlchemyStorage, **kwargs):
        return await storage.messages.create(Message(**kwargs))
