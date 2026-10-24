import pytest
from sqlalchemy import make_url

from harp_apps.storage.utils.migrations import create_alembic_config


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://bench@localhost/bench?host=/run/postgresql",
        "postgresql+asyncpg://bench:p%40ss%25@db.example/bench",
        "sqlite+aiosqlite:///:memory:?cache=shared",
    ],
)
def test_url_reaches_alembic_unchanged(url):
    config = create_alembic_config(url)
    assert make_url(config.get_main_option("sqlalchemy.url")) == make_url(url)
