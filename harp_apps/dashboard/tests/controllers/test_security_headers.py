from typing import cast
from unittest.mock import AsyncMock, Mock

from httpx import AsyncClient
from multidict import CIMultiDict

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.http import HttpRequest, HttpResponse
from harp.views.json import json
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.controllers.blobs import INERT_BLOB_HEADERS
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.storage.types import IStorage

DASHBOARD_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)


def _create_controller(settings: DashboardSettings = None):
    controller = DashboardController(
        storage=cast(IStorage, Mock(spec=IStorage)),
        settings=settings or DashboardSettings(auth={"type": "none"}, devserver={"enabled": True, "port": 5173}),
        http_client=Mock(spec=AsyncClient),
    )
    controller._ui_devserver_proxy_controller = None
    return controller


def _assert_security_headers(headers):
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["content-security-policy"] == DASHBOARD_CSP


async def test_api_responses_carry_security_headers():
    response = await _create_controller()(HttpRequest(path="/api/nope"), AsyncMock())

    assert response.status == 404
    _assert_security_headers(response.headers)


async def test_json_views_carry_security_headers():
    controller = _create_controller()
    controller._handle = AsyncMock(return_value=json({"a": 1}))

    response = await controller(HttpRequest(path="/api/system"), AsyncMock())

    assert response.status == 200
    assert response.content_type == "application/json"
    assert response.body == b'{"a":1}'
    _assert_security_headers(response.headers)


async def test_default_login_gate_carries_security_headers():
    controller = _create_controller(DashboardSettings(devserver={"enabled": True, "port": 5173}))

    response = await controller(HttpRequest(path="/api/system"), AsyncMock())

    assert response.status == 401
    assert response.headers["www-authenticate"].startswith("Basic")
    _assert_security_headers(response.headers)


async def test_unauthorized_responses_carry_security_headers():
    controller = _create_controller(
        DashboardSettings(
            auth=BasicAuthSettings(type="basic", algorithm="plaintext", users={"admin": User(password="admin")}),
            devserver={"enabled": True, "port": 5173},
        )
    )

    response = await controller(HttpRequest(path="/"), AsyncMock())

    assert response.status == 401
    _assert_security_headers(response.headers)


async def test_static_assets_carry_security_headers(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!DOCTYPE html><title>HARP</title>")
    monkeypatch.setattr(DashboardController, "static_build_path", str(tmp_path))
    controller = _create_controller(DashboardSettings(auth={"type": "none"}))
    sent = []

    async def asgi_send(message):
        sent.append(message)

    request = HttpRequest(HttpRequestAsgiBridge({"type": "http", "method": "GET", "path": "/"}, AsyncMock()))
    await controller(request, asgi_send)

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 200
    _assert_security_headers(CIMultiDict((k.decode(), v.decode()) for k, v in start["headers"]))


async def test_client_side_routes_get_the_index(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<title>HARP</title>")
    monkeypatch.setattr(DashboardController, "static_build_path", str(tmp_path))
    controller = _create_controller(DashboardSettings(auth={"type": "none"}))
    sent = []

    async def asgi_send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/transactions/abc"}
    await controller(HttpRequest(HttpRequestAsgiBridge(scope, AsyncMock())), asgi_send)

    assert next(m for m in sent if m["type"] == "http.response.start")["status"] == 200
    assert b"".join(m.get("body", b"") for m in sent) == b"<title>HARP</title>"


async def test_devserver_responses_get_no_content_security_policy():
    controller = _create_controller()
    controller._ui_devserver_proxy_controller = AsyncMock(return_value=HttpResponse(b"<html></html>"))

    response = await controller(HttpRequest(path="/"), AsyncMock())

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" not in response.headers


async def test_a_stricter_policy_set_by_a_handler_is_kept():
    controller = _create_controller()
    controller._handle = AsyncMock(return_value=HttpResponse(b"", headers=INERT_BLOB_HEADERS))

    response = await controller(HttpRequest(path="/api/blobs/x"), AsyncMock())

    assert response.headers.getall("content-security-policy") == ["sandbox; default-src 'none'"]
