"""Storage Application"""

from functools import partial
from os.path import dirname
from pathlib import Path
from typing import cast

from sqlalchemy import StaticPool, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from harp import get_logger
from harp.config import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnShutdownEvent
from harp_apps.storage.models import Base
from harp_apps.storage.settings import StorageSettings
from harp_apps.storage.types import IStorage
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


async def on_bind(event: OnBindEvent):
    settings: StorageSettings = cast(StorageSettings, event.settings["storage"])

    # SQLAlchemy Engine
    # Created directly because of migrations, way easier to ensure the database is up and ready for whatever needs
    # it. Of course, it'd be better to have async factories, but that's not the case (yet).

    database_url = make_url(str(settings.url))

    if database_url.get_dialect() == "sqlite" and database_url.database == ":memory:":
        engine = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_async_engine(database_url)

    if settings.migrate:
        await _run_migrations(engine)
    event.container.add_instance(engine, AsyncEngine)

    # load service definitions, bound to our settings
    event.container.load(Path(dirname(__file__)) / "services.yml", bind_settings=settings)

    event.container.add_singleton(StorageAsyncWorkerQueue)


async def on_bound(event: OnBoundEvent):
    storage = event.provider.get(IStorage)
    await storage.initialize()
    await storage.ready()
    worker = event.provider.get(StorageAsyncWorkerQueue)
    worker.register_events(event.dispatcher)


async def on_shutdown(event: OnShutdownEvent):
    worker = event.provider.get(StorageAsyncWorkerQueue)
    await worker.wait_until_empty()
    await event.provider.get(IStorage).finalize()


application = Application(
    settings_type=StorageSettings,
    on_bind=on_bind,
    on_bound=on_bound,
    on_shutdown=on_shutdown,
)
