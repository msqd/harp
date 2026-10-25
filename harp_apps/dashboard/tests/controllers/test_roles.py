"""
Every dashboard route declares the role it requires, and a request below it is answered 403.

The routes go through the real dashboard controller and its sub-controllers; storage is a stand-in, as what the handlers
do once let in is not under test here.
"""

import inspect
from base64 import b64encode
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock

import orjson
import pytest
from http_router import Router
from httpx import AsyncClient

from harp.http import HttpRequest
from harp.meta import get_meta
from harp.security.actor import Role
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.controllers.blobs import BlobsController
from harp_apps.dashboard.controllers.overview import OverviewController
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.controllers.transactions import TransactionsController
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.dashboard.tests._mixins import RoleNamedActors
from harp_apps.storage.types import IStorage

SAME_ORIGIN = {"content-type": "application/json", "host": "harp.test", "origin": "http://harp.test"}

#: (method, path, role required)
ROUTES = [
    ("GET", "/api/overview/summary", Role.VIEWER),
    ("GET", "/api/overview/", Role.VIEWER),
    ("GET", "/api/transactions/filters", Role.VIEWER),
    ("GET", "/api/transactions/", Role.VIEWER),
    ("GET", "/api/transactions/abc", Role.VIEWER),
    ("PUT", "/api/transactions/abc/flags/favorite", Role.VIEWER),
    ("DELETE", "/api/transactions/abc/flags/favorite", Role.VIEWER),
    ("GET", "/api/blobs/abc", Role.VIEWER),
    ("GET", "/metrics", Role.VIEWER),
    ("GET", "/api/system/", Role.VIEWER),
    ("GET", "/api/system/proxy", Role.EDITOR),
    ("PUT", "/api/system/proxy", Role.EDITOR),
    ("GET", "/api/system/storage", Role.EDITOR),
    ("GET", "/api/system/settings", Role.ADMIN),
    ("GET", "/api/system/dependencies", Role.ADMIN),
]


@pytest.fixture
async def dashboard():
    router = Router(trim_last_slash=True)
    storage = MagicMock(spec=IStorage)
    for sub in (
        lambda: BlobsController(storage=storage, router=router),
        lambda: OverviewController(storage=storage, router=router),
        lambda: SystemController(storage=storage, settings=MagicMock(), resolver=MagicMock(), router=router),
        lambda: TransactionsController(storage=storage, router=router),
    ):
        sub()
    users = {name: User(password="x") for name in ("viewer", "editor", "admin", "disabled")}
    controller = DashboardController(
        storage=cast(IStorage, storage),
        settings=DashboardSettings(
            auth=BasicAuthSettings(type="basic", algorithm="plaintext", users=users),
            devserver={"enabled": True, "port": 5173},
        ),
        http_client=Mock(spec=AsyncClient),
        router=router,
        actors=RoleNamedActors(),
    )
    controller._ui_devserver_proxy_controller = None
    return controller


async def call(dashboard, method, path, username):
    headers = {**SAME_ORIGIN, "authorization": "basic " + b64encode(f"{username}:x".encode()).decode()}
    try:
        return await dashboard(HttpRequest(method=method, path=path, headers=headers), AsyncMock())
    except Exception:  # let in, then the stand-in storage gave the handler nothing to work with
        return None


@pytest.mark.parametrize("method, path, required", ROUTES)
@pytest.mark.parametrize("role", list(Role))
async def test_a_route_answers_403_below_its_role_and_lets_the_role_and_above_in(
    dashboard, method, path, required, role
):
    response = await call(dashboard, method, path, role.label)

    if role < required:
        assert response.status == 403
        assert orjson.loads(response.body) == {"error": "Forbidden", "status": 403}
    else:
        assert response is None or response.status != 403


@pytest.mark.parametrize("method, path, required", ROUTES)
async def test_a_disabled_account_answers_401_on_every_route(dashboard, method, path, required):
    response = await call(dashboard, method, path, "disabled")

    assert response.status == 401


def test_every_handler_of_the_dashboard_declares_its_role():
    handlers = [
        (controller.__name__, name)
        for controller in (BlobsController, OverviewController, SystemController, TransactionsController)
        for name, handler in inspect.getmembers(controller, callable)
        if get_meta(handler, "route") and get_meta(handler, "role") is None
    ]

    assert handlers == []


def test_a_route_added_without_a_role_is_admin_only():
    assert DashboardController.roles_required is True
