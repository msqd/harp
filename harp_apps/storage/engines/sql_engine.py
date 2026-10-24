from typing import Any, Union

from pydantic_core import MultiHostUrl
from sqlalchemy import URL, AsyncAdaptedQueuePool, event, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine

from harp import get_logger

logger = get_logger(__name__)


def warn_if_database_is_deprecated(url: Union[str, URL]) -> None:
    """Log one line for MySQL/MariaDB (both use the mysql dialect). Never the url: it may carry a password."""
    if make_url(str(url)).get_backend_name() == "mysql":
        logger.warning(
            "MySQL/MariaDB storage is deprecated and will be removed in a future version. PostgreSQL is the "
            "supported production database."
        )


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


# Long enough to ride out a checkpoint or a slow disk, short enough that a stuck writer surfaces as an error.
SQLITE_BUSY_TIMEOUT_MS = 10_000


def enforce_sqlite_foreign_keys(cursor) -> None:
    """SQLite ignores foreign keys, so every ``ON DELETE CASCADE`` is inert, unless each connection asks for them."""
    cursor.execute("PRAGMA foreign_keys=ON")


def enforce_sqlite_foreign_keys_on_connect(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        enforce_sqlite_foreign_keys(cursor)
    finally:
        cursor.close()


def configure_sqlite_connection(dbapi_connection, _record) -> None:
    """Write-ahead log: readers and the one writer no longer block each other, which rollback-journal mode does."""
    cursor = dbapi_connection.cursor()
    try:
        enforce_sqlite_foreign_keys(cursor)
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


class SQLAlchemyEngine(AsyncEngine):
    @staticmethod
    def from_url(url: MultiHostUrl) -> AsyncEngine:
        database_url = make_url(str(url))
        if database_url.get_backend_name() == "sqlite" and database_url.database == ":memory:":
            # The database lives in its one connection, so every user must share it, one at a time: a
            # connection shared at once (StaticPool) lets a reader's rollback undo a concurrent writer's
            # uncommitted insert. A pool of exactly one queues the users instead.
            engine = create_async_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=AsyncAdaptedQueuePool,
                pool_size=1,
                max_overflow=0,
            )
            event.listen(engine.sync_engine, "connect", enforce_sqlite_foreign_keys_on_connect)
            return engine

        engine = create_async_engine(database_url)
        if database_url.get_backend_name() == "sqlite":
            event.listen(engine.sync_engine, "connect", configure_sqlite_connection)
        return engine
