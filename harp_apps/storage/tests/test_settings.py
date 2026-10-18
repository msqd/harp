import importlib.util
import re

import pytest
from pydantic import ValidationError

from harp.config import Application
from harp.config.asdict import asdict
from harp_apps.storage.settings import StorageSettings


def test_empty_settings():
    settings = StorageSettings()

    assert asdict(settings, verbose=True) == {
        "enabled": True,
        "migrate": True,
        "early_insert_after": 1.0,
        "pending_max_age": 3600.0,
        "flush_interval": 1.0,
        "flush_batch_size": 500,
        "pending_max_bytes": 67108864,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "sql"},
        "redis": None,
    }

    assert asdict(settings) == {}


def test_secure():
    settings = StorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings, verbose=True, mode="python") == {
        "enabled": True,
        "migrate": True,
        "early_insert_after": 1.0,
        "pending_max_age": 3600.0,
        "flush_interval": 1.0,
        "flush_batch_size": 500,
        "pending_max_bytes": 67108864,
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
        "blobs": {"type": "sql"},
        "redis": None,
    }

    assert asdict(settings, mode="python") == {
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
    }

    assert asdict(settings, verbose=True, secure=False) == {
        "enabled": True,
        "migrate": True,
        "early_insert_after": 1.0,
        "pending_max_age": 3600.0,
        "flush_interval": 1.0,
        "flush_batch_size": 500,
        "pending_max_bytes": 67108864,
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
        "blobs": {"type": "sql"},
        "redis": None,
    }

    assert asdict(settings, secure=False) == {
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
    }


def test_override_blob_storage_type():
    settings = StorageSettings.from_kwargs(blobs={"type": "redis"})
    assert asdict(settings, verbose=True) == {
        "enabled": True,
        "migrate": True,
        "early_insert_after": 1.0,
        "pending_max_age": 3600.0,
        "flush_interval": 1.0,
        "flush_batch_size": 500,
        "pending_max_bytes": 67108864,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "redis"},
        "redis": None,
    }

    assert asdict(settings) == {
        "blobs": {"type": "redis"},
    }


def test_override_redis_url():
    settings = StorageSettings.from_kwargs(blobs={"type": "redis"}, redis={"url": "redis://example.com:1234/42"})
    assert asdict(settings, verbose=True) == {
        "blobs": {"type": "redis"},
        "enabled": True,
        "migrate": True,
        "early_insert_after": 1.0,
        "pending_max_age": 3600.0,
        "flush_interval": 1.0,
        "flush_batch_size": 500,
        "pending_max_bytes": 67108864,
        "redis": {"url": "redis://example.com:1234/42"},
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
    }
    assert asdict(settings) == {
        "blobs": {"type": "redis"},
        "redis": {"url": "redis://example.com:1234/42"},
    }


def test_settings_normalization_does_not_hide_password():
    app = Application(settings_type=StorageSettings)
    settings = app.normalize({"url": "postgresql://user:password@localhost:5432/db"})
    assert settings["url"] == "postgresql+asyncpg://user:password@localhost:5432/db"


def test_asyncmy_refused():
    with pytest.raises(ValidationError, match=r"mysql\+aiomysql://"):
        StorageSettings(url="mysql+asyncmy://user:password@localhost:3306/db")


@pytest.mark.parametrize(
    ("url", "module", "extra"),
    [
        ("postgresql://user:password@localhost:5432/db", "asyncpg", "postgresql"),
        ("postgresql+asyncpg://user:password@localhost:5432/db", "asyncpg", "postgresql"),
        ("mysql://user:password@localhost:3306/db", "aiomysql", "mysql"),
        ("mysql+aiomysql://user:password@localhost:3306/db", "aiomysql", "mysql"),
    ],
)
def test_missing_driver_names_the_extra(monkeypatch, url, module, extra):
    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name, *a, **kw: None if name == module else real_find_spec(name, *a, **kw)
    )

    with pytest.raises(ValidationError, match=re.escape(f"pip install harp-proxy[{extra}]")):
        StorageSettings(url=url)


def test_sqlite_needs_no_extra(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **kw: None)

    assert StorageSettings(url="sqlite:///:memory:").url.scheme == "sqlite+aiosqlite"
