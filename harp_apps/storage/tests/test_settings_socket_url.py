import pytest
from pydantic import ValidationError
from sqlalchemy import make_url

from harp_apps.storage.engines import SQLAlchemyEngine
from harp_apps.storage.settings import StorageSettings


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://bench@/bench?host=/run/postgresql",
        "postgresql+asyncpg://bench:secret@/bench?host=/run/postgresql&port=5433",
        "postgresql://bench@/bench?host=/run/postgresql",
    ],
)
def test_unix_socket_url_with_an_empty_host_is_accepted(url):
    settings = StorageSettings(url=url)
    sqlalchemy_url = make_url(str(settings.url))
    assert sqlalchemy_url.drivername == "postgresql+asyncpg"
    assert sqlalchemy_url.username == "bench"
    assert sqlalchemy_url.database == "bench"
    assert sqlalchemy_url.query["host"] == "/run/postgresql"


def test_socket_directory_is_what_the_driver_connects_to():
    settings = StorageSettings(url="postgresql+asyncpg://bench@/bench?host=/run/postgresql&port=5433")
    engine = SQLAlchemyEngine.from_url(settings.url)
    _, arguments = engine.dialect.create_connect_args(engine.url)
    assert (arguments["host"], arguments["port"]) == ("/run/postgresql", 5433)


def test_empty_host_without_a_socket_directory_is_still_refused():
    with pytest.raises(ValidationError, match="empty host"):
        StorageSettings(url="postgresql+asyncpg://bench@/bench")
