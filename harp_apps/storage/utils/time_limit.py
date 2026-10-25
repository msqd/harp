import asyncio
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from harp_apps.storage.errors import StorageTimeLimitExceeded

_POSTGRESQL_QUERY_CANCELED = "57014"


async def execute_with_time_limit(session: AsyncSession, statement, *, time_limit: Optional[float]):
    """
    Execute a statement in the session, stopped by the database when it runs longer than ``time_limit`` seconds (any
    time, ``None`` for no bound), raising :class:`StorageTimeLimitExceeded` instead of a database exception.

    - PostgreSQL: ``statement_timeout``, scoped to the current transaction.
    - SQLite: no server-side setting, so an asyncio timeout, then the running query is interrupted.
    - Other dialects (MySQL and MariaDB are unsupported): no time limit.
    """
    if time_limit is None:
        return await session.execute(statement)

    dialect = session.bind.dialect.name
    try:
        if dialect == "postgresql":
            return await _execute_postgresql(session, statement, time_limit)
        if dialect == "sqlite":
            return await _execute_sqlite(session, statement, time_limit)
        return await session.execute(statement)
    except DBAPIError as exc:
        if _is_time_limit_error(exc):
            raise StorageTimeLimitExceeded(time_limit) from exc
        raise


def _is_time_limit_error(exc: DBAPIError) -> bool:
    orig = exc.orig
    if getattr(orig, "sqlstate", None) == _POSTGRESQL_QUERY_CANCELED:
        return True
    if getattr(getattr(orig, "__cause__", None), "sqlstate", None) == _POSTGRESQL_QUERY_CANCELED:
        return True
    return False


async def _execute_postgresql(session, statement, time_limit):
    await session.execute(
        text("SELECT set_config('statement_timeout', :milliseconds, true)"),
        {"milliseconds": str(max(1, int(time_limit * 1000)))},
    )
    return await session.execute(statement)


async def _execute_sqlite(session, statement, time_limit):
    connection = await session.connection()
    raw = await connection.get_raw_connection()
    task = asyncio.ensure_future(session.execute(statement))
    done, _ = await asyncio.wait({task}, timeout=time_limit)
    if task in done:
        return task.result()

    await raw.driver_connection.interrupt()
    try:
        await task
    except DBAPIError:
        pass
    raise StorageTimeLimitExceeded(time_limit)
