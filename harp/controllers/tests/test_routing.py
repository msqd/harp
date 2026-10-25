import orjson
import pytest
from structlog.testing import capture_logs

import harp
from harp.controllers import GetHandler, PutHandler, RoutingController
from harp.http import HttpRequest, HttpResponse
from harp.security.actor import Actor, ActorAccount, Role, set_actor
from harp.utils.arguments import Arguments


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


class RoleController(RoutingController):
    @GetHandler("/view", role=Role.VIEWER)
    async def view(self):
        return "view"

    @PutHandler("/edit", role=Role.EDITOR)
    async def edit(self):
        return "edit"

    @GetHandler("/undeclared")
    async def undeclared(self):
        return "undeclared"


class StrictRoleController(RoleController):
    roles_required = True


def _request(method, path, role=None):
    request = HttpRequest(method=method, path=path)
    if role:
        set_actor(request, Actor(account=ActorAccount(id=1, username="alice", role=role), role=role, via="basic"))
    return request


async def test_a_handler_runs_for_an_actor_with_its_role_or_above():
    controller = RoleController()

    assert await controller(_request("PUT", "/edit", Role.EDITOR)) == "edit"
    assert await controller(_request("PUT", "/edit", Role.ADMIN)) == "edit"


async def test_a_handler_refuses_an_actor_below_its_role_with_403():
    response = await RoleController()(_request("PUT", "/edit", Role.VIEWER))

    assert response.status == 403
    assert orjson.loads(response.body) == {"error": "Forbidden", "status": 403}


async def test_a_handler_with_a_role_refuses_a_request_without_actor_with_401():
    response = await RoleController()(_request("GET", "/view"))

    assert response.status == 401


async def test_a_handler_without_role_is_open_unless_the_controller_requires_roles():
    assert await RoleController()(_request("GET", "/undeclared")) == "undeclared"


async def test_a_controller_requiring_roles_treats_an_undeclared_handler_as_admin_only():
    controller = StrictRoleController()

    assert (await controller(_request("GET", "/undeclared", Role.EDITOR))).status == 403
    assert await controller(_request("GET", "/undeclared", Role.ADMIN)) == "undeclared"


class RefusalAwareController(RoleController):
    def __init__(self, **kwargs):
        self.refused = []
        super().__init__(**kwargs)

    async def on_refusal(self, request, handler):
        self.refused.append(handler.__name__)


async def test_a_refusal_tells_the_controller_before_it_is_sent():
    controller = RefusalAwareController()

    response = await controller(_request("PUT", "/edit", Role.VIEWER))

    assert (response.status, controller.refused) == (403, ["edit"])


async def test_a_permitted_request_is_not_a_refusal():
    controller = RefusalAwareController()

    await controller(_request("PUT", "/edit", Role.EDITOR))

    assert controller.refused == []


async def test_a_refusal_reaches_the_sub_controller_owning_the_handler_through_a_shared_router():
    router = RoutingController.RouterType(trim_last_slash=True)
    owner = RefusalAwareController(router=router)
    front = RoutingController(router=router)

    response = await front(_request("PUT", "/edit", Role.VIEWER))

    assert (response.status, owner.refused) == (403, ["edit"])


class UnresolvableController(RoutingController):
    @GetHandler("/unresolvable")
    async def unresolvable(self, missing):
        raise AssertionError("handler must not run with an unresolved argument")


async def test_unresolvable_handler_argument_is_a_500_not_a_call(monkeypatch):
    monkeypatch.setattr(harp, "DEBUG", False)
    response = await UnresolvableController()(HttpRequest(method="GET", path="/unresolvable"))
    assert response.status == 500
    assert orjson.loads(response.body) == {"error": "TypeError", "status": 500}


async def test_router_arguments_reach_the_router_as_keywords():
    class StrictSlashController(BoomController):
        RouterArguments = Arguments(trim_last_slash=False)

    response = await StrictSlashController()(HttpRequest(method="GET", path="/boom/"))
    assert response.status == 404


async def test_handler_parameter_defaults_apply_on_static_routes():
    class DefaultsController(RoutingController):
        @GetHandler("/items")
        async def items(self, request, page=1):
            return HttpResponse(str(page))

    response = await DefaultsController()(HttpRequest(method="GET", path="/items"))
    assert (response.status, response.body) == (200, b"1")
