from typing import cast

from rodi import Container

from harp.utils.services import factory

from ..settings import DatabaseSettings


def register_database_service(container: Container, settings: DatabaseSettings):
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

    database_url = _get_database_url(settings.url)

    @factory(AsyncEngine)
    def AsyncEngineFactory(self) -> AsyncEngine:
        nonlocal database_url
        return create_async_engine(database_url)

    container.add_singleton(AsyncEngine, cast(type, AsyncEngineFactory))
    container.set_alias("database", AsyncEngine)


def _get_database_url(settings_url):
    from sqlalchemy import make_url

    database_url = make_url(str(settings_url))
    if database_url.get_driver_name() == "psycopg2":
        database_url = database_url.set(drivername="postgresql+asyncpg")
    return str(database_url)
