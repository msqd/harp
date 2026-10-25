import orjson
import pytest
from structlog.testing import capture_logs

import harp
from harp.controllers import GetHandler, RoutingController
from harp.http import HttpRequest


class BoomController(RoutingController):
    @GetHandler("/boom")
    async def boom(self):
        raise RuntimeError("SECRET-MESSAGE")


async def _call(path):
    return await BoomController()(HttpRequest(method="GET", path=path))


async def test_error_is_json_without_traceback_when_not_debug(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", False)
    response = await _call("/boom")
    assert response.status == 500
    assert response.headers["content-type"].startswith("application/json")
    assert orjson.loads(response.body) == {"error": "RuntimeError", "status": 500}
    assert b"Traceback" not in response.body


async def test_error_carries_traceback_when_debug(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", True)
    response = await _call("/boom")
    body = orjson.loads(response.body)
    assert body["status"] == 500
    assert "Traceback" in body["traceback"]


async def test_traceback_is_logged_whatever_debug(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", False)
    with capture_logs() as logs:
        await _call("/boom")
    assert any(entry.get("exc_info") for entry in logs)


@pytest.mark.parametrize("debug", [False, True])
async def test_not_found_is_json(monkeypatch, debug):
    monkeypatch.setattr(harp, "DEBUG", debug)
    response = await _call("/nope")
    assert response.status == 404
    assert orjson.loads(response.body)["status"] == 404


class UnresolvableController(RoutingController):
    @GetHandler("/unresolvable")
    async def unresolvable(self, missing):
        raise AssertionError("handler must not run with an unresolved argument")


async def test_unresolvable_handler_argument_is_a_500_not_a_call(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", False)
    response = await UnresolvableController()(HttpRequest(method="GET", path="/unresolvable"))
    assert response.status == 500
    assert orjson.loads(response.body) == {"error": "TypeError", "status": 500}
