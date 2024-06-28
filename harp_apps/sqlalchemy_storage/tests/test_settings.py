from harp.config import asdict
from harp_apps.sqlalchemy_storage.settings import SqlAlchemyStorageSettings


def test_empty_settings():
    settings = SqlAlchemyStorageSettings()

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///harp.db",
        "blobs": {"type": "sql"},
    }


def test_secure():
    settings = SqlAlchemyStorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "postgresql://user:***@localhost:5432/db",
        "blobs": {"type": "sql"},
    }
    assert asdict(settings, secure=False) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "postgresql://user:password@localhost:5432/db",
        "blobs": {"type": "sql"},
    }


def test_override():
    settings = SqlAlchemyStorageSettings(url="sqlite+aiosqlite:///toto.db")

    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///toto.db",
        "blobs": {"type": "sql"},
    }

    settings.url = settings.url.set(database=":memory:")
    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///:memory:",
        "blobs": {"type": "sql"},
    }


def test_override_blob_storage_type():
    settings = SqlAlchemyStorageSettings(blobs={"type": "redis"})
    assert asdict(settings) == {
        "migrate": True,
        "type": "sqlalchemy",
        "url": "sqlite+aiosqlite:///harp.db",
        "blobs": {"type": "redis"},
    }
