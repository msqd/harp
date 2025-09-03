from harp.config import Application
from harp.config.asdict import asdict
from harp_apps.storage.settings import StorageSettings


def test_empty_settings():
    settings = StorageSettings()

    assert asdict(settings, verbose=True) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "sql"},
        "redis": None,
        "skip_storage_requests_payload": [],
        "skip_storage_responses_payload": [],
    }

    assert asdict(settings) == {}


def test_secure():
    settings = StorageSettings(url="postgresql://user:password@localhost:5432/db")

    assert asdict(settings, verbose=True, mode="python") == {
        "migrate": True,
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
        "blobs": {"type": "sql"},
        "redis": None,
        "skip_storage_requests_payload": [],
        "skip_storage_responses_payload": [],
    }

    assert asdict(settings, mode="python") == {
        "url": "postgresql+asyncpg://user:***@localhost:5432/db",
    }

    assert asdict(settings, verbose=True, secure=False) == {
        "migrate": True,
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
        "blobs": {"type": "sql"},
        "redis": None,
        "skip_storage_requests_payload": [],
        "skip_storage_responses_payload": [],
    }

    assert asdict(settings, secure=False) == {
        "url": "postgresql+asyncpg://user:password@localhost:5432/db",
    }


def test_override_blob_storage_type():
    settings = StorageSettings.from_kwargs(blobs={"type": "redis"})
    assert asdict(settings, verbose=True) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "redis"},
        "redis": None,
        "skip_storage_requests_payload": [],
        "skip_storage_responses_payload": [],
    }

    assert asdict(settings) == {
        "blobs": {"type": "redis"},
    }


def test_override_redis_url():
    settings = StorageSettings.from_kwargs(blobs={"type": "redis"}, redis={"url": "redis://example.com:1234/42"})
    assert asdict(settings, verbose=True) == {
        "blobs": {"type": "redis"},
        "migrate": True,
        "redis": {"url": "redis://example.com:1234/42"},
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "skip_storage_requests_payload": [],
        "skip_storage_responses_payload": [],
    }
    assert asdict(settings) == {
        "blobs": {"type": "redis"},
        "redis": {"url": "redis://example.com:1234/42"},
    }


def test_settings_normalization_does_not_hide_password():
    app = Application(settings_type=StorageSettings)
    settings = app.normalize({"url": "postgresql://user:password@localhost:5432/db"})
    assert settings["url"] == "postgresql+asyncpg://user:password@localhost:5432/db"


def test_skip_storage_payload_settings():
    settings = StorageSettings.from_kwargs(
        skip_storage_requests_payload=["/api/uploads/*", "/health"], skip_storage_responses_payload=["/api/downloads/*"]
    )

    assert asdict(settings, verbose=True) == {
        "migrate": True,
        "url": "sqlite+aiosqlite:///:memory:?cache=shared",
        "blobs": {"type": "sql"},
        "redis": None,
        "skip_storage_requests_payload": ["/api/uploads/*", "/health"],
        "skip_storage_responses_payload": ["/api/downloads/*"],
    }

    assert asdict(settings) == {
        "skip_storage_requests_payload": ["/api/uploads/*", "/health"],
        "skip_storage_responses_payload": ["/api/downloads/*"],
    }


def test_matches_any_pattern_matching():
    import re

    from harp_apps.storage.worker import matches_any

    patterns = [re.compile(r"/api/uploads/.*"), re.compile(r"/health")]

    # Test matching cases
    assert matches_any("/api/uploads/file.txt", patterns)
    assert matches_any("/health", patterns)
    assert matches_any("/api/uploads/subfolder/image.png", patterns)

    # Test non-matching cases
    assert not matches_any("/api/downloads/file.txt", patterns)
    assert not matches_any("/status", patterns)
