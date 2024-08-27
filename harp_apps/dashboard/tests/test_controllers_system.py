import re
from unittest.mock import ANY

from harp.utils.testing import RE
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.databases import parametrize_with_blob_storages_urls, parametrize_with_database_urls
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

from ..controllers import SystemController
from ._mixins import SystemControllerTestFixtureMixin, parametrize_with_settings


class TestSystemController(
    SystemControllerTestFixtureMixin,
    StorageTestFixtureMixin,
):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_empty(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": {"type": "sql"},
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
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": {"type": "redis"},
                "migrate": True,
                "url": "sqlite+aiosqlite:///:memory:",
                "redis": {"url": "redis://redis.example.com:1234/42"},
            },
        }

    @parametrize_with_settings({"storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "blobs": ANY,
                "migrate": True,
                "url": "sqlite+aiosqlite:///:memory:",
                "redis": None,
            },
        }

    @parametrize_with_settings({"applications": ["storage"]})
    @parametrize_with_database_urls("postgresql")
    async def test_get_settings_sqlalchemy_secure(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "migrate": True,
                "url": RE(r".*://test:\*\*\*@.*"),
                "blobs": ANY,
                "redis": None,
            },
        }


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
            b':memory:","migrate":true,"blobs":{"type":"sql"},"redis":null}}'
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
            b':memory:","migrate":true,"blobs":{"type":"redis"},"redis":null}}'
        )

    @parametrize_with_settings({"applications": ["storage"], "storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_sqlalchemy(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","migrate":true,"blobs":{"type":"sql"},"redis":null}}'
        )

    @parametrize_with_settings(
        {"applications": ["storage"], "storage": {"url": "sqlite+aiosqlite:///:memory:", "blobs": {"type": "redis"}}}
    )
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("redis")
    async def test_get_settings_sqlalchemy_blobs_in_redis(self, client: ASGICommunicator):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"url":"sqlite+aiosqlite:///'
            b':memory:","migrate":true,"blobs":{"type":"redis"},"redis":null}}'
        )

    @parametrize_with_database_urls("postgresql")
    @parametrize_with_blob_storages_urls("sql")
    async def test_get_settings_sqlalchemy_secure(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == RE(
            re.escape(b'{"applications":["harp_apps.storage"],"storage":{"url":"postgresql+asyncpg://test:***@')
            + b".*:\\d+"  # host and port number will vary
            + re.escape(b'/test_b238114489d2135dfbd3b9b5ddfc56ab","migrate":true,"blobs":{"type":"sql"},"redis":null}}')
        )

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
            b':memory:","migrate":true,"blobs":{"type":"redis"},"redis":{"url":"redis://us'
            b'er:***@localhost:6379/0"}}}'
        )
