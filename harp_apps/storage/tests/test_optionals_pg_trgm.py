import random
import string
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DatabaseError, ProgrammingError

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.storage.optionals.pg_trgm import PgTrgmOptional
from harp_apps.storage.utils.sql import run_sql
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin
from harp_apps.storage.utils.testing.sql import run_cli_migrate_command


async def get_indexes(engine, table_name):
    return [
        row[0]
        for row in (
            await run_sql(
                engine,
                f"SELECT indexname FROM pg_indexes WHERE tablename = '{table_name}';",
            )
        ).fetchall()
    ]


def generate_random_db_name(length=5):
    characters = string.ascii_lowercase + string.digits
    return "test_" + "".join(random.choice(characters) for _ in range(length))


@parametrize_with_database_urls("postgresql")
async def test_pg_trgm(database_url):
    opt = PgTrgmOptional(database_url)

    # cannot execute because it needs the database to contain something first.
    with pytest.raises(ProgrammingError):
        await opt.install()

    # run the migrations
    result = await run_cli_migrate_command(database_url)
    assert result.exit_code == 0

    # we should not have gin indexes yet
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")

    # now we can actually install our optimized indexes
    await opt.install()

    # extension and indexes should exist now
    assert await opt._is_pg_trgm_extension_installed()
    assert "messages_summary_gin" in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" in await get_indexes(opt.engine, "transactions")

    # let's uninstall
    await opt.uninstall()

    # we should not have gin indexes anymore, but the extension should still be there
    assert await opt._is_pg_trgm_extension_installed()
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")


@parametrize_with_database_urls("postgresql")
async def test_pg_trgm_on_database_without_create_extension_privilege(database_url):
    opt = PgTrgmOptional(database_url)

    # simulate a database without the privilege to create extensions
    opt._is_pg_trgm_extension_installed = AsyncMock(return_value=False)
    opt._install_pg_trgm_extension_if_possible = AsyncMock(side_effect=DatabaseError("nope.", None, Exception()))
    assert not await opt._is_pg_trgm_extension_installed()

    # run the migrations
    result = await run_cli_migrate_command(database_url)
    assert result.exit_code == 0

    # we should not have gin indexes ...
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")

    await opt.install()

    # ... but neither after upgrade
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")


@parametrize_with_database_urls("mysql", "sqlite")
async def test_pg_trgm_not_available_for_non_postgres_databases(database_url):
    opt = PgTrgmOptional(database_url)

    # cannot install on not supported dialects
    with pytest.raises(RuntimeError):
        await opt.install()


class TestOptimizedQueries(StorageTestFixtureMixin):
    @parametrize_with_database_urls("postgresql")
    async def test_optimized_queries(self, sql_storage):
        # store raw sql queries in `storage.sql_queries`, please
        sql_storage.install_debugging_instrumentation()

        opt = PgTrgmOptional(sql_storage.engine.url)
        try:
            await opt.install()

            result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="bar")

            # count + select
            assert len(sql_storage.sql_queries) == 2

            for _ in range(100):
                await self.create_transaction(
                    sql_storage,
                    endpoint="/api/transactions/foo/bar/baz",
                    tags={"foo": "bar"},
                )

            result = await sql_storage.get_transaction_list(username="anonymous", with_messages=True, text_search="bar")

            assert len(result) == 40
            # first queries, then count + select + flags,tags,messages
            assert len(sql_storage.sql_queries) == 2 + 2 + 3

        finally:
            await opt.engine.dispose()
