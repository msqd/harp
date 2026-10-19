import logging

import pytest

from harp_apps.storage.engines import warn_if_database_is_deprecated

LOGGER = "harp_apps.storage.engines.sql_engine"


@pytest.mark.parametrize(
    "url",
    [
        "mysql+aiomysql://user:s3cret@localhost/harp",
        "mariadb+aiomysql://user:s3cret@localhost/harp",
    ],
)
def test_mysql_and_mariadb_warn_once_without_leaking_the_url(url, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        warn_if_database_is_deprecated(url)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "deprecated" in message
    assert "PostgreSQL" in message
    assert "s3cret" not in message
    assert "localhost" not in message


@pytest.mark.parametrize("url", ["postgresql+asyncpg://user:pw@localhost/harp", "sqlite+aiosqlite:///:memory:"])
def test_postgresql_and_sqlite_do_not_warn(url, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        warn_if_database_is_deprecated(url)

    assert caplog.records == []
