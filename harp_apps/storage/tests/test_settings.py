from harp.config import Application, asdict
from harp_apps.storage.settings import StorageSettings


def test_empty_settings():
    settings = StorageSettings()

    assert asdict(settings, verbose=True) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "sql"},
    }

    assert asdict(settings) == {}


def test_secure():
    settings = StorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings, verbose=True, mode="python") == {
        "migrate": True,
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
        "blobs": {"type": "sql"},
    }

    assert asdict(settings, mode="python") == {
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
    }

    assert asdict(settings, verbose=True, secure=False) == {
        "migrate": True,
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
        "blobs": {"type": "sql"},
    }

    assert asdict(settings, secure=False) == {
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
    }


def test_override_blob_storage_type():
    settings = StorageSettings.from_kwargs(blobs={"type": "redis"})
    assert asdict(settings, verbose=True) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "redis", "url": "redis://localhost:6379/0"},
    }

    assert asdict(settings) == {
        "blobs": {"type": "redis"},
    }


def test_settings_normalization_does_not_hide_password():
    app = Application(settings_type=StorageSettings)
    settings = app.normalize({"url": "postgresql://user:password@localhost:5432/db"})
    assert settings["url"] == "postgresql+asyncpg://user:password@localhost:5432/db"
