import orjson
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.http import HttpRequest
from harp.security.actor import Actor, ActorAccount, Role, set_actor
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.databases import parametrize_with_blob_storages_urls, parametrize_with_database_urls
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp.views.json import register as register_json_views
from harp_apps.audit.models import AuditEvent
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.tests._mixins import SystemControllerTestFixtureMixin, parametrize_with_settings
from harp_apps.proxy.constants import CHECKING, UP
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

SETTINGS = {
    "applications": ["proxy", "http_client", "storage", "audit"],
    "proxy": {"endpoints": [{"name": "api", "port": 4000, "url": "http://user:secret@127.0.0.1:1/"}]},
}


def actor_with(role: Role) -> Actor:
    return Actor(account=ActorAccount(id=7, username="ed", role=role), role=role, via="basic")


class ActingFixtureMixin(ControllerThroughASGIFixtureMixin):
    """The dashboard resolves the actor of a request: here it is an account with the role of the test."""

    role = Role.EDITOR

    @pytest.fixture
    def kernel(self, controller):
        async def as_actor(request):
            set_actor(request, actor_with(self.role))
            return await controller(request)

        kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=as_actor), handle_errors=False)
        register_json_views(kernel.dispatcher)
        return kernel


async def put_proxy(client: ASGICommunicator, **data):
    return await client.http_request(
        "PUT",
        "/api/system/proxy",
        body=orjson.dumps({"endpoint": "api", "index": 0, **data}),
        headers=[(b"content-type", b"application/json"), (b"user-agent", b"Firefox/141")],
    )


async def audit_rows(sql_storage) -> list[AuditEvent]:
    async with sql_storage.session_factory() as session:
        return list((await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars())


def remote_status(controller: SystemController) -> int:
    (endpoint,) = controller.resolver.endpoints.values()
    return endpoint.remote.endpoints[0].status


class TestManualRemoteStateChange(SystemControllerTestFixtureMixin, StorageTestFixtureMixin, ActingFixtureMixin):
    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_an_editor_change_is_recorded_with_the_editor_as_actor(
        self, client, controller, sql_storage, blob_storage
    ):
        response = await put_proxy(client, action="down")

        assert response["status"] == 200
        (row,) = await audit_rows(sql_storage)
        assert (row.action, row.outcome) == ("proxy.remote.state_changed", "succeeded")
        assert (row.actor_account_id, row.actor_label, row.actor_via) == (7, "ed", "basic")
        assert row.user_agent == "Firefox/141"
        assert (row.target_type, row.target_label) == ("remote", "api")
        assert row.details == {"endpoint": "api", "url": "http://127.0.0.1:1/", "from": "checking", "to": "down"}

    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_a_manual_change_is_not_also_logged_as_an_automatic_one(
        self, client, controller, sql_storage, blob_storage
    ):
        with capture_logs() as logs:
            await put_proxy(client, action="down")

        assert [log["kind"] for log in logs if "kind" in log] == ["audit"]

    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_a_rejected_request_records_nothing(self, client, controller, sql_storage, blob_storage):
        response = await put_proxy(client, action="down", index=3)

        assert response["status"] == 404
        assert await audit_rows(sql_storage) == []
        assert remote_status(controller) == CHECKING

    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_a_commit_failing_after_the_change_restores_the_previous_state(
        self, controller, sql_storage, blob_storage, monkeypatch
    ):
        await controller.put_proxy(self.put_request("up"))
        assert remote_status(controller) == UP

        async def failing_commit(session):
            raise RuntimeError("commit failed")

        monkeypatch.setattr(AsyncSession, "commit", failing_commit)
        with pytest.raises(RuntimeError, match="commit failed"):
            await controller.put_proxy(self.put_request("down"))
        monkeypatch.undo()

        assert remote_status(controller) == UP
        assert [row.details["to"] for row in await audit_rows(sql_storage)] == ["up"]

    def put_request(self, action: str) -> HttpRequest:
        request = HttpRequest(body=orjson.dumps({"endpoint": "api", "index": 0, "action": action}))
        set_actor(request, actor_with(self.role))
        return request


class TestRefusedRemoteStateChange(SystemControllerTestFixtureMixin, StorageTestFixtureMixin, ActingFixtureMixin):
    role = Role.VIEWER

    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_a_refused_attempt_is_recorded_as_denied_and_changes_nothing(
        self, client, controller, sql_storage, blob_storage
    ):
        response = await put_proxy(client, action="down")

        assert response["status"] == 403
        assert remote_status(controller) == CHECKING
        (row,) = await audit_rows(sql_storage)
        assert (row.action, row.outcome) == ("proxy.remote.state_changed", "denied")
        assert (row.actor_account_id, row.actor_label) == (7, "ed")
        assert row.details == {
            "endpoint": "api",
            "url": "http://127.0.0.1:1/",
            "from": "checking",
            "to": "down",
            "required_role": "editor",
        }

    @parametrize_with_settings(SETTINGS)
    @parametrize_with_database_urls("sqlite")
    @parametrize_with_blob_storages_urls("sql")
    async def test_a_refused_attempt_with_an_unreadable_body_is_still_refused(
        self, client, controller, sql_storage, blob_storage
    ):
        response = await client.http_request(
            "PUT", "/api/system/proxy", body=b"nope", headers=[(b"content-type", b"application/json")]
        )

        assert response["status"] == 403
        (row,) = await audit_rows(sql_storage)
        assert row.outcome == "denied"
        assert row.details == {"required_role": "editor"}
