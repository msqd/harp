from typing import Any, Union

from pydantic_core import MultiHostUrl
from sqlalchemy import URL, AsyncAdaptedQueuePool, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine


def create_async_engine(url: Union[str, URL], **kw: Any) -> AsyncEngine:
    url = make_url(url)
    kw.setdefault("connect_args", {})

    if url.get_dialect() == "postgresql":
        kw["connect_args"].setdefault("server_settings", {})
        # This is necessary so that postgres always send back utc datetimes, we'll handle timezone specific logic
        # ourselves to avoid differences between environments. Override at your own risk.
        kw["connect_args"]["server_settings"].setdefault("timezone", "UTC")
    elif url.get_dialect().name == "mysql":
        # Same for MySQL: TIMESTAMP values are converted to and from the session timezone, which defaults to
        # the server's. Pinning the session to UTC makes grace comparisons independent of the server.
        kw["connect_args"].setdefault("init_command", "SET time_zone = '+00:00'")
    engine = _create_async_engine(url, **kw)
    return engine


class SQLAlchemyEngine(AsyncEngine):
    @staticmethod
    def from_url(url: MultiHostUrl) -> AsyncEngine:
        database_url = make_url(str(url))
        if database_url.get_backend_name() == "sqlite" and database_url.database == ":memory:":
            # The database lives in its one connection, so every user must share it, one at a time: a
            # connection shared at once (StaticPool) lets a reader's rollback undo a concurrent writer's
            # uncommitted insert. A pool of exactly one queues the users instead.
            return create_async_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=AsyncAdaptedQueuePool,
                pool_size=1,
                max_overflow=0,
            )

        return create_async_engine(database_url)
