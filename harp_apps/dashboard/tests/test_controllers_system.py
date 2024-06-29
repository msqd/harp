from copy import deepcopy
from unittest.mock import ANY

import pytest

from harp import Config
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.databases import parametrize_with_database_urls
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

from ..controllers import SystemController


class SystemControllerTestFixtureMixin:
    @pytest.fixture
    def controller(self, request, storage, blob_storage):
        # retrieve settings overrides
        raw_settings = deepcopy(request.param)
        raw_settings.setdefault("storage", {})
        raw_settings["storage"].setdefault("blobs", {})
        raw_settings["storage"]["blobs"].setdefault("type", blob_storage.type)
        config = Config(raw_settings)
        settings = config.validate()
        return SystemController(storage=storage, settings=settings, handle_errors=False)


def parametrize_with_settings(*args):
    return pytest.mark.parametrize("controller", args, indirect=True)


class TestSystemController(
    SystemControllerTestFixtureMixin,
    StorageTestFixtureMixin,
):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_empty(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {"applications": []}

    @parametrize_with_settings({"applications": ["storage"], "storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "migrate": True,
                "type": "sqlalchemy",
                "url": "sqlite+aiosqlite:///:memory:",
                "blobs": {"type": ANY},
            },
        }

    @parametrize_with_settings(
        {"applications": ["storage"], "storage": {"url": "postgresql://user:password@localhost:5432/db"}}
    )
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy_secure(self, controller: SystemController):
        response = await controller.get_settings()
        assert response == {
            "applications": ["harp_apps.storage"],
            "storage": {
                "migrate": True,
                "type": "sqlalchemy",
                "url": "postgresql://user:***@localhost:5432/db",
                "blobs": {"type": ANY},
            },
        }


class TestSystemControllerThroughASGI(
    SystemControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_empty(self, client: ASGICommunicator):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == b'{"applications":[]}'

    @parametrize_with_settings({"applications": ["storage"], "storage": {"url": "sqlite+aiosqlite:///:memory:"}})
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"type":"sqlalche'
            b'my","url":"sqlite+aiosqlite:///:memory:","migrate":true,"blobs":{"type":"'
            + blob_storage.type.encode()
            + b'"}}}'
        )

    @parametrize_with_settings(
        {"applications": ["storage"], "storage": {"url": "postgresql://user:password@localhost:5432/db"}}
    )
    @parametrize_with_database_urls("sqlite")
    async def test_get_settings_sqlalchemy_secure(self, client: ASGICommunicator, blob_storage):
        response = await client.http_get("/api/system/settings")

        assert response["status"] == 200
        assert response["headers"] == ((b"content-type", b"application/json"),)
        assert response["body"] == (
            b'{"applications":["harp_apps.storage"],"storage":{"type":"sqlalche'
            b'my","url":"postgresql://user:***@localhost:5432/db","migrate":true,"blobs":{'
            b'"type":"' + blob_storage.type.encode() + b'"}}}'
        )
