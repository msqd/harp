from harp.config import asdict
from harp_apps.sqlalchemy_storage.settings import SqlAlchemyStorageSettings


def test_empty_settings():
    settings = SqlAlchemyStorageSettings()

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///harp.db",
    }


def test_secure():
    settings = SqlAlchemyStorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "postgresql://user:***@localhost:5432/db",
    }
    assert asdict(settings, secure=False) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "postgresql://user:password@localhost:5432/db",
    }


def test_override():
    settings = SqlAlchemyStorageSettings(url="sqlite+aiosqlite:///toto.db")

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///toto.db",
    }

    settings.url = settings.url.set(database=":memory:")
    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///:memory:",
    }
