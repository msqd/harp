"""
Reading the audit: Admins page through everything, every account reads only what concerns it.
"""

from datetime import UTC, datetime, timedelta

import orjson
import pytest
from multidict import MultiDict

from harp.http import HttpRequest
from harp.security.actor import Actor, ActorAccount, Role, set_actor
from harp_apps.audit.models import AuditEvent
from harp_apps.dashboard.controllers.audit import AuditController
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def request_of(account_id, role=Role.ADMIN, **query):
    request = HttpRequest(method="GET")
    request.query = MultiDict(query)
    set_actor(
        request,
        Actor(account=ActorAccount(id=account_id, username=f"acc{account_id}", role=role), role=role, via="basic"),
    )
    return request


def event(minutes_ago=0, **fields) -> AuditEvent:
    return AuditEvent(
        **{
            "occurred_at": NOW - timedelta(minutes=minutes_ago),
            "action": "auth.signed_in",
            "outcome": "succeeded",
            "actor_via": "session",
            "actor_account_id": 1,
            "actor_label": "alice",
            "ip": "10.0.0.1",
            "user_agent": "Firefox",
            **fields,
        }
    )


def body(response) -> dict:
    return orjson.loads(orjson.dumps(dict(response)))


class TestAuditController(StorageTestFixtureMixin):
    @pytest.fixture
    def controller(self, sql_storage):
        return AuditController(storage=sql_storage, handle_errors=False)

    async def seed(self, storage, *events):
        async with storage.session_factory() as session:
            session.add_all(events)
            await session.commit()

    async def test_events_come_newest_first(self, controller, sql_storage):
        await self.seed(sql_storage, event(30, action="old"), event(0, action="new"), event(10, action="mid"))

        page = body(await controller.list(request_of(9)))

        assert [item["action"] for item in page["items"]] == ["new", "mid", "old"]
        assert page["total"] == 3

    async def test_an_event_is_shown_with_its_fields(self, controller, sql_storage):
        await self.seed(
            sql_storage,
            event(
                target_type="account",
                target_id="7",
                target_label="bob",
                details={"method": "password"},
            ),
        )

        (item,) = body(await controller.list(request_of(9)))["items"]

        assert item["occurredAt"] == "2026-10-25T12:00:00Z"
        assert (item["action"], item["outcome"]) == ("auth.signed_in", "succeeded")
        assert (item["actor"]["id"], item["actor"]["label"], item["actor"]["via"]) == (1, "alice", "session")
        assert (item["ip"], item["userAgent"]) == ("10.0.0.1", "Firefox")
        assert item["target"] == {"type": "account", "id": "7", "label": "bob"}
        assert item["details"] == {"method": "password"}

    async def test_events_are_paginated(self, controller, sql_storage):
        await self.seed(sql_storage, *(event(minutes) for minutes in range(41)))

        first = body(await controller.list(request_of(9)))
        second = body(await controller.list(request_of(9, page="2")))

        assert (len(first["items"]), first["pages"], first["perPage"], first["total"]) == (40, 2, 40, 41)
        assert len(second["items"]) == 1

    async def test_filters_by_period(self, controller, sql_storage):
        await self.seed(sql_storage, event(120, action="a"), event(60, action="b"), event(0, action="c"))

        page = body(
            await controller.list(
                request_of(
                    9,
                    since=(NOW - timedelta(minutes=90)).isoformat(),
                    until=(NOW - timedelta(minutes=30)).isoformat(),
                )
            )
        )

        assert [item["action"] for item in page["items"]] == ["b"]

    async def test_a_period_given_as_days_is_read_as_utc(self, controller, sql_storage):
        await self.seed(sql_storage, event(60 * 24 * 3, action="before"), event(0, action="inside"))

        page = body(await controller.list(request_of(9, since="2026-10-24", until="2026-10-26")))

        assert [item["action"] for item in page["items"]] == ["inside"]

    async def test_filters_by_actor_username(self, controller, sql_storage):
        await self.seed(sql_storage, event(actor_label="alice"), event(actor_label="bob"))

        page = body(await controller.list(request_of(9, actor="bob")))

        assert [item["actor"]["label"] for item in page["items"]] == ["bob"]

    async def test_filters_by_action_prefix(self, controller, sql_storage):
        await self.seed(
            sql_storage,
            event(action="auth.signed_in"),
            event(action="auth.token.created"),
            event(action="proxy.remote.state_changed"),
        )

        page = body(await controller.list(request_of(9, action="auth.")))

        assert sorted(item["action"] for item in page["items"]) == ["auth.signed_in", "auth.token.created"]

    async def test_an_action_filter_is_a_prefix_not_a_pattern(self, controller, sql_storage):
        await self.seed(sql_storage, event(action="auth.signed_in"))

        page = body(await controller.list(request_of(9, action="%")))

        assert page["items"] == []

    async def test_filters_by_target(self, controller, sql_storage):
        await self.seed(
            sql_storage,
            event(target_type="account", target_id="7"),
            event(target_type="account", target_id="8"),
            event(target_type="remote", target_id="7"),
        )

        page = body(await controller.list(request_of(9, target_type="account", target_id="7")))

        assert [(item["target"]["type"], item["target"]["id"]) for item in page["items"]] == [("account", "7")]

    async def test_my_activity_is_what_the_account_did_or_what_was_done_to_it(self, controller, sql_storage):
        await self.seed(
            sql_storage,
            event(3, action="did", actor_account_id=5),
            event(2, action="suffered", actor_account_id=6, target_type="account", target_id="5"),
            event(1, action="others", actor_account_id=6, target_type="account", target_id="7"),
            event(0, action="system", actor_account_id=None),
        )

        page = body(await controller.mine(request_of(5, role=Role.VIEWER)))

        assert [item["action"] for item in page["items"]] == ["suffered", "did"]
        assert page["total"] == 2

    async def test_my_activity_can_be_narrowed_by_filters_never_widened(self, controller, sql_storage):
        await self.seed(sql_storage, event(actor_account_id=6, actor_label="bob"))

        page = body(await controller.mine(request_of(5, role=Role.EDITOR, actor="bob")))

        assert page["items"] == []

    async def test_a_target_with_the_same_id_but_another_type_is_not_my_account(self, controller, sql_storage):
        await self.seed(sql_storage, event(actor_account_id=6, target_type="remote", target_id="5"))

        page = body(await controller.mine(request_of(5, role=Role.VIEWER)))

        assert page["items"] == []

    async def test_my_activity_hides_where_someone_else_acted_from(self, controller, sql_storage):
        await self.seed(
            sql_storage,
            event(1, action="by-me", actor_account_id=5, actor_via_id="211", actor_client="cli"),
            event(
                0,
                action="by-admin",
                actor_account_id=6,
                actor_via_id="9",
                actor_client="mcp",
                target_type="account",
                target_id="5",
            ),
        )

        by_admin, by_me = body(await controller.mine(request_of(5, role=Role.VIEWER)))["items"]

        assert (by_me["ip"], by_me["userAgent"]) == ("10.0.0.1", "Firefox")
        assert (by_me["actor"]["viaId"], by_me["actor"]["client"]) == ("211", "cli")
        assert (by_admin["ip"], by_admin["userAgent"]) == (None, None)
        assert (by_admin["actor"]["viaId"], by_admin["actor"]["client"]) == (None, None)

    async def test_a_request_without_an_account_id_has_no_activity(self, controller, sql_storage):
        await self.seed(sql_storage, event(actor_account_id=None))

        page = body(await controller.mine(request_of(None, role=Role.VIEWER)))

        assert page["items"] == []

    async def test_a_period_that_is_not_a_date_is_a_bad_request(self, controller, sql_storage):
        response = await controller.list(request_of(9, since="yesterday"))

        assert response.status == 400
