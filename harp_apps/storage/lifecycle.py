from functools import partial
from typing import cast

from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from harp import get_logger
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent
from harp_apps.storage.factories import RedisClientFactory
from harp_apps.storage.models import Base
from harp_apps.storage.services import SqlStorage
from harp_apps.storage.settings import StorageSettings
from harp_apps.storage.types import IBlobStorage, IStorage
from harp_apps.storage.worker import StorageAsyncWorkerQueue

logger = get_logger(__name__)


async def _run_migrations(engine: AsyncEngine):
    if engine.dialect.name == "sqlite" and engine.url.database == ":memory:":  # pragma: no cover
        # in memory sqlite won't be able to reconnect to the same instance, so we create the tables directly
        async with engine.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    else:
        # todo refactor ? see harp_apps.storage.utils.testing.mixins.StorageTestFixtureMixin
        from alembic import command

        from harp_apps.storage.utils.migrations import create_alembic_config, do_migrate

        alembic_cfg = create_alembic_config(engine.url.render_as_string(hide_password=False))
        migrator = partial(command.upgrade, alembic_cfg, "head")
        await do_migrate(engine, migrator=migrator)


class StorageLifecycle:
    @staticmethod
    async def on_bind(event: FactoryBindEvent):
        settings: StorageSettings = event.settings.get("storage")

        # SQLAlchemy Engine
        # Created directly because of migrations, way easier to ensure the database is up and ready for whatever needs
        # it. Of course, it'd be better to have async factories, but that's not the case (yet).

        if settings.url.get_dialect() == "sqlite" and settings.url.database == ":memory:":
            engine = create_async_engine(settings.url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        else:
            engine = create_async_engine(settings.url)

        if settings.migrate:
            await _run_migrations(engine)
        event.container.add_instance(engine, AsyncEngine)

        event.container.add_singleton(IStorage, SqlStorage)

        blob_storage_type = settings.blobs.type

        if blob_storage_type == "sql":
            from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage

            if IBlobStorage in event.container:
                del event.container._map[IBlobStorage]
            event.container.add_singleton(IBlobStorage, SqlBlobStorage)
        elif blob_storage_type == "redis":
            from redis.asyncio import Redis

            from harp_apps.storage.services.blob_storages.redis import RedisBlobStorage

            event.container.add_singleton(Redis, cast(type, RedisClientFactory))

            if IBlobStorage in event.container:
                del event.container._map[IBlobStorage]
            event.container.add_singleton(IBlobStorage, RedisBlobStorage)
        else:
            raise ValueError(f"Unsupported blob storage type: {blob_storage_type}")

        event.container.add_singleton(StorageAsyncWorkerQueue)

    @staticmethod
    async def on_bound(event: FactoryBoundEvent):
        storage = event.provider.get(IStorage)
        await storage.initialize()
        await storage.ready()
        worker = event.provider.get(StorageAsyncWorkerQueue)
        worker.register_events(event.dispatcher)

    @staticmethod
    async def on_dispose(event: FactoryDisposeEvent):
        worker = event.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()
        await event.provider.get(IStorage).finalize()
