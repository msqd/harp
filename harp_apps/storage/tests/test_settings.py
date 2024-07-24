from harp.config import asdict
from harp_apps.storage.settings import StorageSettings


def test_empty_settings():
    settings = StorageSettings()

    assert asdict(settings) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "sql"},
    }


def test_secure():
    settings = StorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings) == {
        "migrate": True,
        "url": "postgresql://user:***@localhost:5432/db",
        "blobs": {"type": "sql"},
    }
    assert asdict(settings, secure=False) == {
        "migrate": True,
        "url": "postgresql://user:password@localhost:5432/db",
        "blobs": {"type": "sql"},
    }


def test_override():
    settings = StorageSettings(url="sqlite+aiosqlite:///toto.db")

    assert asdict(settings) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///toto.db",
        "blobs": {"type": "sql"},
    }

    settings.url = settings.url.set(database="foo.db")
    assert asdict(settings) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///foo.db",
        "blobs": {"type": "sql"},
    }


def test_override_blob_storage_type():
    settings = StorageSettings(blobs={"type": "redis"})
    assert asdict(settings) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "redis", "url": "redis://localhost:6379/0"},
    }
