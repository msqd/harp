import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from structlog.testing import capture_logs

from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.unit_of_work import ANY_EVENT, TransactionalEventDispatcher, auditable
from harp.unit_of_work.audit import Actor, AuditableEvent, Target
from harp_apps.audit.models import AuditEvent
from harp_apps.audit.recorder import AuditRecorder
from harp_apps.storage.unit_of_work import SqlUnitOfWorkFactory, current_session


@auditable("test.role_changed")
class RoleChanged(AuditableEvent):
    details_fields = ("from", "to")


@auditable("test.token_created")
class TokenCreated(AuditableEvent):
    details_fields = ("prefix", "name")


@auditable("test.bare")
class Bare(AuditableEvent):
    pass


@pytest.fixture
async def session_factory(sql_engine):
    async with sql_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE audit_probe_actions (note VARCHAR(50))"))
    return async_sessionmaker(sql_engine, expire_on_commit=False)


@pytest.fixture
def unit_of_work(session_factory):
    transactional = TransactionalEventDispatcher()
    transactional.add_listener(ANY_EVENT, AuditRecorder().write)
    return SqlUnitOfWorkFactory(session_factory, transactional=transactional, dispatcher=LoggingAsyncEventDispatcher())


async def rows(session_factory) -> list[AuditEvent]:
    async with session_factory() as session:
        return list((await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars())


async def actions(session_factory) -> list[str]:
    async with session_factory() as session:
        return [row[0] for row in await session.execute(text("SELECT note FROM audit_probe_actions"))]


async def change_role(unit_of_work, event):
    async with unit_of_work() as uow:
        await current_session().execute(text("INSERT INTO audit_probe_actions (note) VALUES ('role changed')"))
        await uow.record(event)


def role_changed(**kwargs):
    return RoleChanged(
        actor=Actor(
            account_id=1, label="alice", via="session", via_id="tok_8f3a", ip="10.0.4.12", user_agent="Firefox/141"
        ),
        target=Target("account", 7, "bob"),
        details={"from": "viewer", "to": "editor"},
        **kwargs,
    )


async def test_the_event_is_written_in_the_commit_of_its_action(unit_of_work, session_factory):
    await change_role(unit_of_work, role_changed())

    assert await actions(session_factory) == ["role changed"]
    (row,) = await rows(session_factory)
    assert (row.action, row.outcome) == ("test.role_changed", "succeeded")
    assert (row.actor_account_id, row.actor_label, row.actor_via, row.actor_via_id) == (
        1,
        "alice",
        "session",
        "tok_8f3a",
    )
    assert (row.ip, row.user_agent) == ("10.0.4.12", "Firefox/141")
    assert (row.target_type, row.target_id, row.target_label) == ("account", "7", "bob")
    assert row.details == {"from": "viewer", "to": "editor"}
    assert row.occurred_at is not None


async def test_a_system_actor_has_no_account(unit_of_work, session_factory):
    await change_role(unit_of_work, RoleChanged(target=Target("invitation", 3, "setup")))

    (row,) = await rows(session_factory)
    assert (row.actor_account_id, row.actor_via) == (None, "system")


async def test_a_failing_audit_write_rolls_back_the_action(unit_of_work, session_factory):
    # `actor_via` is NOT NULL: the insert of the audit row fails, after the action wrote its own row
    event = RoleChanged(actor=Actor(via=None))

    with pytest.raises(Exception):
        await change_role(unit_of_work, event)

    assert await actions(session_factory) == []
    assert await rows(session_factory) == []


async def test_a_failing_action_leaves_no_audit_row(unit_of_work, session_factory):
    with pytest.raises(RuntimeError, match="action failed"):
        async with unit_of_work() as uow:
            await uow.record(role_changed())
            raise RuntimeError("action failed")

    assert await rows(session_factory) == []


LEAKS = [
    {"name": "password", "value": "hunter2"},
    {"pwd": "hunter2"},
    {"key": "hunter2"},
    {"auth": "hunter2"},
    {"recovery_codes": ["hunter2"]},
    {"cmd": "Authorization: hunter2"},
    {"token": "hrp_hunter2"},
]


@pytest.mark.parametrize("leak", LEAKS)
async def test_undeclared_details_are_never_persisted_nor_logged(unit_of_work, session_factory, leak):
    event = TokenCreated(target=Target("token", 5, "ci"), details={"prefix": "hrp_ab", "name": "ci", **leak})

    with capture_logs() as logs:
        await change_role(unit_of_work, event)

    (row,) = await rows(session_factory)
    assert set(row.details) == {"prefix", "name"}
    assert "hunter2" not in str(row.details)
    assert "hunter2" not in str(logs)  # neither the audit line nor the warning about the dropped fields


async def test_dropped_details_are_reported_by_name(unit_of_work):
    with capture_logs() as logs:
        await change_role(unit_of_work, TokenCreated(details={"prefix": "hrp_ab", "token": "hrp_hunter2"}))

    (warning,) = [entry for entry in logs if entry["log_level"] == "warning"]
    assert warning["dropped"] == ["token"]


async def test_an_event_without_declared_fields_records_no_details(unit_of_work, session_factory):
    await change_role(unit_of_work, Bare(details={"anything": 1}))

    (row,) = await rows(session_factory)
    assert row.details == {}


@auditable("test.with_meta")
class WithMeta(AuditableEvent):
    details_fields = ("meta", "scopes", "count")


@pytest.mark.parametrize("meta", [{"password": "hunter2"}, [{"password": "hunter2"}], [["hunter2"]]])
async def test_declared_fields_hold_scalars_only(unit_of_work, session_factory, meta):
    event = WithMeta(details={"meta": meta, "scopes": ["read", "write"], "count": 2})

    with capture_logs() as logs:
        await change_role(unit_of_work, event)

    (row,) = await rows(session_factory)
    assert row.details == {"scopes": ["read", "write"], "count": 2}
    assert "hunter2" not in str(logs)
    (warning,) = [entry for entry in logs if entry["log_level"] == "warning"]
    assert warning["dropped"] == ["meta"]


async def test_the_log_line_is_written_after_the_commit_only(unit_of_work, session_factory):
    with capture_logs() as logs:
        await change_role(unit_of_work, role_changed())

    (line,) = [entry for entry in logs if entry.get("kind") == "audit"]
    assert line["action"] == "test.role_changed"
    assert (line["outcome"], line["actor_account_id"], line["actor_label"]) == ("succeeded", 1, "alice")
    assert (line["target_type"], line["target_id"], line["target_label"]) == ("account", "7", "bob")
    assert line["details"] == {"from": "viewer", "to": "editor"}
    assert line["id"] == (await rows(session_factory))[0].id


async def test_nothing_is_logged_when_the_unit_of_work_rolls_back(unit_of_work):
    with capture_logs() as logs, pytest.raises(RuntimeError):
        async with unit_of_work() as uow:
            await uow.record(role_changed())
            raise RuntimeError("action failed")

    assert [entry for entry in logs if entry.get("kind") == "audit"] == []
