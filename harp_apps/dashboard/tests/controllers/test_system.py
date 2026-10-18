import logging
from re import escape
from unittest.mock import ANY, patch

import orjson

from harp.utils.testing import RE
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.databases import parametrize_with_blob_storages_urls, parametrize_with_database_urls
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.tests._mixins import SystemControllerTestFixtureMixin, parametrize_with_settings
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestSystemController(
    SystemControllerTestFixtureMixin,
    StorageTestFixtureMixin,
):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_empty(self, controller: SystemController):
        response = await controller.get_settings()
        assert response.asdict() == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": {"type": "sql"},
                "enabled": True,
                "migrate": True,
                "url": "sqlite+aiosqlite:///:memory:",
                "redis": None,
            },
        }

    @parametrize_with_settings({"storage": {"redis": {"url": "redis://redis.example.com:1234/42"}}})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("redis")
    async def test_get_settings_redis(self, controller: SystemController):
        response = await controller.get_settings()
        assert response.asdict() == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": {"type": "redis"},
                "enabled": True,
                "migrate": True,
                "url": "sqlite+aiosqlite:///:memory:",
                "redis": {"url": "redis://redis.example.com:1234/42"},
            },
        }

    @parametrize_with_settings({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy(self, controller: SystemController):
        response = await controller.get_settings()
        assert response.asdict() == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": ANY,
                "enabled": True,
                "migrate": True,
                "url": "sqlite+aiosqlite:///:memory:",
                "redis": None,
            },
        }

    @parametrize_with_settings({"applications": ["storage"]})
    @parametrize_with_database_urls("postgresql")
    async def test_get_settings_sqlalchemy_secure(self, controller: SystemController):
        response = await controller.get_settings()
        assert response.asdict() == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "enabled": True,
                "migrate": True,
                "url": RE(r".*://test:\*\*\*@.*"),
                "blobs": ANY,
                "redis": None,
            },
        }

    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_dependencies_success(self, controller: SystemController):
        """Test that get_dependencies returns a dict of installed packages."""
        response = await controller.get_dependencies()

        assert "python" in response
        assert isinstance(response["python"], dict)
        assert len(response["python"]) > 0
        # Verify some package exists with a version
        assert any(version != "unknown" for version in response["python"].values())

    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_dependencies_handles_errors_gracefully(self, controller: SystemController):
        """Test that get_dependencies returns empty dict when dependency detection fails."""
        # Reset cache to ensure test isolation
        controller._dependencies = None

        with patch("harp_apps.dashboard.controllers.system.get_python_dependencies") as mock_get_deps:
            # Simulate a complete failure in dependency detection
            mock_get_deps.side_effect = Exception("Simulated dependency detection failure")

            response = await controller.get_dependencies()

            # Should return empty dict instead of crashing
            assert response == {"python": {}}


class TestSystemControllerThroughASGI(
    SystemControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_empty(self, client: ASGICommunicator):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","enabled":true,"migrate":true,"blobs":{"type":"sql"},"redis":null}}'
        )

    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("redis")
    async def test_get_settings_empty_redis(self, client: ASGICommunicator):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","enabled":true,"migrate":true,"blobs":{"type":"redis"},"redis":null}}'
        )

    @parametrize_with_settings(
        {
            "applications": ["storage"],
            "storage": {"url": "sqlite+aiosqlite:///:memory:"},
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_sqlalchemy(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","enabled":true,"migrate":true,"blobs":{"type":"sql"},"redis":null}}'
        )

    @parametrize_with_settings(
        {
            "applications": ["storage"],
            "storage": {
                "url": "sqlite+aiosqlite:///:memory:",
                "blobs": {"type": "redis"},
            },
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("redis")
    async def test_get_settings_sqlalchemy_blobs_in_redis(self, client: ASGICommunicator):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","enabled":true,"migrate":true,"blobs":{"type":"redis"},"redis":null}}'
        )

    @parametrize_with_database_urls("postgresql")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_sqlalchemy_secure(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert orjson.loads(response["body"]) == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": {"type": "sql"},
                "enabled": True,
                "migrate": True,
                "redis": None,
                "url": RE(escape("postgresql+asyncpg://test:***@") + r".*"),
            },
        }

    @parametrize_with_settings(
        {
            "applications": ["storage"],
            "storage": {
                "blobs": {"type": "redis"},
                "redis": {"url": "redis://user:password@localhost:6379/0"},
            },
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("redis")
    async def test_get_settings_sqlalchemy_blobs_in_redis_secure(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","enabled":true,"migrate":true,"blobs":{"type":"redis"},"redis":{"url":"redis://us'
            b'er:***@localhost:6379/0"}}}'
        )

    @parametrize_with_settings(
        {
            "applications": ["http_client", "storage", "dashboard"],
            "storage": {"redis": {"url": "redis://:s3cret@localhost:6379/0"}},
            "dashboard": {"auth": {"type": "basic", "algorithm": "plain", "users": {"alice": "s3cretAlice"}}},
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_masks_every_credential(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert b"s3cret" not in response["body"]

    @parametrize_with_settings(
        {
            "applications": ["proxy", "http_client", "storage", "dashboard"],
            "proxy": {
                "endpoints": [
                    {"name": "api", "port": 4000, "url": "http://user:p%40ss@127.0.0.1:1/"},
                    {"name": "bare", "port": 4001, "url": "http://:p%40ss@127.0.0.1:2/"},
                ],
            },
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_no_system_endpoint_exposes_an_endpoint_password(self, client: ASGICommunicator, blob_storage):
        bodies = {}
        for path in ("/api/system/", "/api/system/settings", "/api/system/proxy", "/api/system/storage"):
            response = await client.http_get(path)
            assert response["status"] == 200, path
            bodies[path] = response["body"]

        assert b"user:***@127.0.0.1:1" in bodies["/api/system/settings"]
        assert b":***@127.0.0.1:2" in bodies["/api/system/settings"]
        for body in bodies.values():
            assert b"p%40ss" not in body
            assert b"p@ss" not in body

    @parametrize_with_settings(
        {
            "applications": ["proxy", "http_client", "storage", "dashboard"],
            "proxy": {"endpoints": [{"name": "api", "port": 4000, "url": "http://user:secret@127.0.0.1:1/"}]},
        }
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_system_endpoints_emit_no_warning_or_log_with_the_password(
        self, client: ASGICommunicator, blob_storage, caplog, recwarn
    ):
        caplog.set_level(logging.DEBUG)
        bodies = []
        for path in ("/api/system/", "/api/system/settings", "/api/system/proxy", "/api/system/storage"):
            response = await client.http_get(path)
            assert response["status"] == 200, path
            bodies.append(response["body"])

        assert b"user:***@127.0.0.1:1" in bodies[2]
        emitted = caplog.text + "\n".join(str(w.message) for w in recwarn.list)
        assert "secret" not in emitted
        assert not [str(w.message)[:300] for w in recwarn.list if "Pydantic serializer" in str(w.message)]
