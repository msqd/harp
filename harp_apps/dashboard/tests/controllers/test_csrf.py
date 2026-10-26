from typing import cast
from unittest.mock import AsyncMock, Mock

import orjson
import pytest
from httpx import AsyncClient

from harp.controllers import RoutingController
from harp.http import HttpRequest, JsonHttpResponse
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.tests._mixins import BASIC_ADMIN_HEADERS, RoleNamedActors, basic_admin_settings
from harp_apps.storage.types import IStorage

STATE_CHANGING_ROUTES = [
    ("PUT", "/api/system/proxy"),
    ("PUT", "/api/transactions/abc/flags/favorite"),
    ("DELETE", "/api/transactions/abc/flags/favorite"),
]

SAME_ORIGIN = {
    "content-type": "application/json",
    "host": "harp.test",
    "origin": "http://harp.test",
    **BASIC_ADMIN_HEADERS,
}


@pytest.fixture
def routed(monkeypatch):
    """The sub-controllers are out of scope here: record whether a request got past the guard."""
    handler = AsyncMock(return_value=JsonHttpResponse({"ok": True}))
    monkeypatch.setattr(RoutingController, "__call__", lambda self, request: handler(request))
    return handler


@pytest.fixture
async def controller():
    controller = DashboardController(
        storage=cast(IStorage, Mock(spec=IStorage)),
        settings=basic_admin_settings(),
        http_client=Mock(spec=AsyncClient),
        actors=RoleNamedActors(),
    )
    controller._ui_devserver_proxy_controller = None
    return controller


async def call(controller, method, path, headers):
    return await controller(HttpRequest(method=method, path=path, headers=headers), AsyncMock())


@pytest.mark.parametrize("method, path", STATE_CHANGING_ROUTES)
async def test_same_origin_json_request_goes_through(controller, routed, method, path):
    response = await call(controller, method, path, SAME_ORIGIN)

    assert response.status == 200
    routed.assert_awaited_once()


@pytest.mark.parametrize("method, path", STATE_CHANGING_ROUTES)
@pytest.mark.parametrize("content_type", [None, "text/plain", "application/x-www-form-urlencoded"])
async def test_request_without_json_content_type_is_refused(controller, routed, method, path, content_type):
    headers = {k: v for k, v in SAME_ORIGIN.items() if k != "content-type"}
    if content_type:
        headers["content-type"] = content_type

    response = await call(controller, method, path, headers)

    assert response.status == 415
    assert orjson.loads(response.body) == {"error": "Content-Type must be application/json", "status": 415}
    assert response.headers["content-type"] == "application/json"
    routed.assert_not_awaited()


@pytest.mark.parametrize("method, path", STATE_CHANGING_ROUTES)
async def test_json_content_type_with_parameters_is_accepted(controller, routed, method, path):
    response = await call(controller, method, path, SAME_ORIGIN | {"content-type": "application/json; charset=utf-8"})

    assert response.status == 200


@pytest.mark.parametrize("method, path", STATE_CHANGING_ROUTES)
@pytest.mark.parametrize(
    "extra",
    [
        {"origin": "http://evil.test"},
        {"origin": "null"},
        {"sec-fetch-site": "cross-site"},
        {"sec-fetch-site": "same-site"},
    ],
)
async def test_cross_site_request_is_refused(controller, routed, method, path, extra):
    response = await call(controller, method, path, SAME_ORIGIN | extra)

    assert response.status == 403
    assert orjson.loads(response.body) == {"error": "Cross-site request refused", "status": 403}
    routed.assert_not_awaited()


@pytest.mark.parametrize("sec_fetch_site", ["same-origin", "none"])
async def test_sec_fetch_site_from_the_dashboard_itself_is_accepted(controller, routed, sec_fetch_site):
    headers = {**BASIC_ADMIN_HEADERS, "content-type": "application/json", "sec-fetch-site": sec_fetch_site}

    response = await call(controller, "PUT", "/api/system/proxy", headers)

    assert response.status == 200


async def test_reads_need_neither_content_type_nor_origin(controller, routed):
    response = await call(controller, "GET", "/api/system", {**BASIC_ADMIN_HEADERS, "origin": "http://evil.test"})

    assert response.status == 200
