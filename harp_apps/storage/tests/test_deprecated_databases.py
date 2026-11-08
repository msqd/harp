import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import make_url

from sqlalchemy.ext.asyncio import AsyncEngine

from harp_apps.storage.__app__ import on_bound
from harp_apps.storage.settings import StorageSettings
from harp_apps.storage.engines import warn_if_database_is_deprecated

LOGGER = "harp_apps.storage.engines.sql_engine"


def test_mysql_warns_once_without_leaking_the_url(caplog):
    url = "mysql+aiomysql://user:s3cret@localhost/harp"
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        warn_if_database_is_deprecated(url)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "unsupported since 0.13" in message
    assert "removed in 0.14" in message
    assert "PostgreSQL" in message
    assert "s3cret" not in message
    assert "localhost" not in message


@pytest.mark.parametrize("url", ["postgresql+asyncpg://user:pw@localhost/harp", "sqlite+aiosqlite:///:memory:"])
def test_postgresql_and_sqlite_do_not_warn(url, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        warn_if_database_is_deprecated(url)

    assert caplog.records == []


async def test_boot_warns_once_for_mysql(caplog):
    engine = MagicMock(url=make_url("mysql+aiomysql://user:s3cret@localhost/harp"))
    provider = MagicMock()
    provider.get.side_effect = lambda t: {StorageSettings: StorageSettings(migrate=False), AsyncEngine: engine}.get(
        t, AsyncMock()
    )
    event = MagicMock(provider=provider, dispatcher=None)

    with patch("harp_apps.storage.utils.migrations.ensure_schema_is_current", AsyncMock()):
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            await on_bound(event)

    assert len(caplog.records) == 1
