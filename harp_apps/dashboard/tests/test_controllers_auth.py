from base64 import b64encode
from typing import cast
from unittest.mock import AsyncMock, Mock

from httpx import AsyncClient

from harp.config import asdict
from harp.http import HttpRequest
from harp.utils.bytes import ensure_bytes
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.storage.types import IBlobStorage, IStorage


async def test_controller_no_auth():
    controller = await _create_mock_controller()
    response = await controller(HttpRequest(), AsyncMock())
    assert response.status == 404


async def test_controller_auth_plaintext():
    controller = await _create_mock_controller(
        settings=DashboardSettings(
            auth=BasicAuthSettings(
                type="basic",
                algorithm="plaintext",
                users={"admin": User(password="admin")},
            )
        )
    )
    assert asdict(controller.settings.auth) == {
        "type": "basic",
        "algorithm": "plaintext",
        "users": {"admin": {"password": "admin"}},
    }

    # no auth? no chance
    response = await controller(HttpRequest(), AsyncMock())
    assert response.status == 401

    # sir, yes sir
    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "admin")), AsyncMock())
    assert response.status == 404

    # wrong password
    response = await controller(HttpRequest(headers=_get_auth_headers("admin", "wrong")), AsyncMock())
    assert response.status == 401


async def _create_mock_controller(settings: DashboardSettings = None):
    return DashboardController(
        storage=cast(IStorage, Mock(spec=IStorage)),
        blob_storage=cast(IBlobStorage, Mock(spec=IBlobStorage)),
        all_settings=Mock(),
        local_settings=settings or DashboardSettings(),
        http_client=Mock(spec=AsyncClient),
        resolver=Mock(),
    )


def _get_auth_headers(username, password):
    return {"authorization": "basic " + b64encode(b":".join((ensure_bytes(username), ensure_bytes(password)))).decode()}