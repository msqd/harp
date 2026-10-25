import time

import pytest
from sqlalchemy import func, select, text

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.errors import StorageTimeLimitExceeded
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.utils.time_limit import execute_with_time_limit

SLOW_SECONDS = 20
TIME_LIMIT = 0.5


def slow_statement(dialect: str):
    """A statement that genuinely runs far longer than the time limit, on each dialect."""
    if dialect == "postgresql":
        return select(func.pg_sleep(SLOW_SECONDS))
    return text(
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 4000000000) SELECT count(*) FROM c"
    )


class TestTimeLimit:
    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_slow_statement_raises_dedicated_error(self, sql_storage: SqlStorage):
        dialect = sql_storage.engine.dialect.name
        started = time.monotonic()

        with pytest.raises(StorageTimeLimitExceeded):
            async with sql_storage.begin() as session:
                await execute_with_time_limit(session, slow_statement(dialect), time_limit=TIME_LIMIT)

        assert time.monotonic() - started < SLOW_SECONDS / 2

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_fast_statement_is_untouched(self, sql_storage: SqlStorage):
        async with sql_storage.begin() as session:
            result = await execute_with_time_limit(
                session, select(func.count()).select_from(text("(select 1) t")), time_limit=TIME_LIMIT
            )

        assert result.scalar() == 1

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_connection_is_usable_after_a_timeout(self, sql_storage: SqlStorage):
        dialect = sql_storage.engine.dialect.name

        with pytest.raises(StorageTimeLimitExceeded):
            async with sql_storage.begin() as session:
                await execute_with_time_limit(session, slow_statement(dialect), time_limit=TIME_LIMIT)

        async with sql_storage.begin() as session:
            assert (await session.scalar(select(func.count()).select_from(text("(select 1) t")))) == 1

    @parametrize_with_database_urls("sqlite", "postgresql")
    async def test_no_time_limit_means_no_bound(self, sql_storage: SqlStorage):
        async with sql_storage.begin() as session:
            result = await execute_with_time_limit(
                session, select(func.count()).select_from(text("(select 1) t")), time_limit=None
            )

        assert result.scalar() == 1
