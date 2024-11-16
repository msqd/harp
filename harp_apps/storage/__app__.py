"""Storage Application"""

from functools import partial
from os.path import dirname
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

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
    # load service definitions, bound to our settings
    event.container.load(Path(dirname(__file__)) / "services.yml", bind_settings=event.settings["storage"])


async def on_bound(event: OnBoundEvent):
    settings = event.provider.get(StorageSettings)
    if settings.migrate:
        engine = event.provider.get(AsyncEngine)
        await _run_migrations(engine)

    storage = event.provider.get(IStorage)
    await storage.initialize()
    await storage.ready()
    worker = event.provider.get(StorageAsyncWorkerQueue)
    if event.dispatcher:
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
