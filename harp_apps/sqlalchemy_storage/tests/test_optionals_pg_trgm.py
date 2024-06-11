import random
import string
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DatabaseError, ProgrammingError

from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.sqlalchemy_storage.optionals.pg_trgm import PgTrgmOptional
from harp_apps.sqlalchemy_storage.utils.testing.database import run_migrations, run_sql


async def get_indexes(engine, table_name):
    return [
        row[0]
        for row in (
            await run_sql(engine, f"SELECT indexname FROM pg_indexes WHERE tablename = '{table_name}';")
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
        await opt.upgrade()

    # run the migrations
    result = await run_migrations(database_url)
    assert result.exit_code == 0

    # we should not have gin indexes yet
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")

    # now we can actually install our optimized indexes
    await opt.upgrade()

    # extension and indexes should exist now
    assert await opt.is_pg_trgm_extension_installed()
    assert "messages_summary_gin" in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" in await get_indexes(opt.engine, "transactions")

    # let's uninstall
    await opt.downgrade()

    # we should not have gin indexes anymore, but the extension should still be there
    assert await opt.is_pg_trgm_extension_installed()
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")


@parametrize_with_database_urls("postgresql")
async def test_pg_trgm_on_database_without_create_extension_privilege(database_url):
    opt = PgTrgmOptional(database_url)

    # simulate a database without the privilege to create extensions
    opt.is_pg_trgm_extension_installed = AsyncMock(return_value=False)
    opt.install_pg_trgm_extension_if_possible = AsyncMock(side_effect=DatabaseError("nope.", None, Exception()))
    assert not await opt.is_pg_trgm_extension_installed()

    # run the migrations
    result = await run_migrations(database_url)
    assert result.exit_code == 0

    # we should not have gin indexes ...
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")

    await opt.upgrade()

    # ... but neither after upgrade
    assert "messages_summary_gin" not in await get_indexes(opt.engine, "messages")
    assert "transactions_endpoint_gin" not in await get_indexes(opt.engine, "transactions")


@parametrize_with_database_urls("mysql", "sqlite")
async def test_pg_trgm_not_available_for_non_postgres_databases(database_url):
    opt = PgTrgmOptional(database_url, echo=True)

    # cannot install on not supported dialects
    with pytest.raises(RuntimeError):
        await opt.upgrade()
