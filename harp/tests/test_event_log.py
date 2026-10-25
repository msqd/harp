import pytest
from pydantic import ValidationError
from config.env import EnvVars
from structlog.testing import capture_logs
from whistle import AsyncEventDispatcher, Event

from harp._logging import logging_config
from harp.config import ApplicationsRegistry, ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.config.core import CoreSettings
from harp.unit_of_work import auditable, loggable
from harp.unit_of_work.event_log import EVENTS_LOGGER, attach_event_log


@loggable("test.eventlog.breaker_opened")
class BreakerOpened(Event):
    details_fields = ("remote",)

    def __init__(self, remote="a", **extra):
        super().__init__()
        self.outcome = "failed"
        self.details = {"remote": remote, **extra}


@loggable("test.eventlog.sign_in_failed")
class SignInFailed(Event):
    pass


@auditable("test.eventlog.audited")
class Audited(Event):
    pass


class Unmarked(Event):
    event_id = "test.eventlog.breaker_opened"  # would be loggable, were the mark not required


def attached(*, muted=()):
    dispatcher = AsyncEventDispatcher()
    attach_event_log(dispatcher, CoreSettings(muted_events=list(muted)))
    return dispatcher


def test_lines_go_to_the_harp_events_logger_which_has_its_own_level():
    assert EVENTS_LOGGER == "harp.events"
    assert logging_config["loggers"]["harp.events"]["level"] == "INFO"


def test_audit_lines_have_their_own_level_apart_from_harp():
    assert logging_config["loggers"]["harp.audit"]["level"] == "INFO"


async def test_a_loggable_event_is_written_as_one_structured_line():
    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.eventlog.breaker_opened", BreakerOpened(remote="upstream"))

    assert len(logs) == 1
    assert logs[0]["kind"] == "event"
    assert logs[0]["event_id"] == "test.eventlog.breaker_opened"
    assert logs[0]["outcome"] == "failed"
    assert logs[0]["details"] == {"remote": "upstream"}
    assert logs[0]["log_level"] == "info"


async def test_only_declared_scalar_details_are_logged():
    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch(
            "test.eventlog.breaker_opened", BreakerOpened(remote="upstream", extra="x", other={"nested": 1})
        )

    assert logs[0]["details"] == {"remote": "upstream"}


async def test_an_event_without_details_is_logged_bare():
    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.eventlog.sign_in_failed", SignInFailed())

    assert logs[0]["event_id"] == "test.eventlog.sign_in_failed"
    assert logs[0]["details"] == {}


async def test_a_muted_event_is_not_logged():
    dispatcher = attached(muted=["test.eventlog.breaker_opened"])

    with capture_logs() as logs:
        await dispatcher.adispatch("test.eventlog.breaker_opened", BreakerOpened())
        await dispatcher.adispatch("test.eventlog.sign_in_failed", SignInFailed())

    assert [log["event_id"] for log in logs] == ["test.eventlog.sign_in_failed"]


@pytest.mark.parametrize("event_id", ["proxy.transaction.started", "test.eventlog.audited", "test.eventlog.unknown"])
def test_muting_what_is_not_loggable_fails_validation(event_id):
    with pytest.raises(ValueError, match=event_id):
        attached(muted=[event_id])


@pytest.mark.parametrize(
    "event_id,event", [("proxy.transaction.started", Unmarked()), ("test.eventlog.audited", Audited())]
)
async def test_an_event_that_is_not_loggable_is_never_logged(event_id, event):
    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch(event_id, event)

    assert logs == []


async def test_an_unmarked_event_dispatched_under_a_loggable_id_is_never_logged():
    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.eventlog.breaker_opened", Unmarked())

    assert logs == []


async def test_a_line_that_cannot_be_built_does_not_break_the_dispatch():
    class Broken(BreakerOpened):
        @property
        def details(self):
            raise RuntimeError("cannot build")

        @details.setter
        def details(self, value):
            pass

    dispatcher = attached()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.eventlog.breaker_opened", Broken())

    assert logs == []


async def test_muting_is_validated_when_the_system_is_built():
    builder = ConfigurationBuilder()
    builder.add_values({"core": {"muted_events": ["proxy.transaction.started"]}})

    with pytest.raises(ValueError, match="proxy.transaction.started"):
        await SystemBuilder(builder.applications, builder.build()).abuild()


def test_the_core_section_defaults_to_muting_nothing():
    assert ConfigurationBuilder().build()["core"] == CoreSettings(muted_events=[])


def test_the_core_section_is_read_from_the_configuration():
    builder = ConfigurationBuilder()
    builder.add_values({"core": {"muted_events": ["a.b"]}})

    assert builder.build()["core"].muted_events == ["a.b"]


def test_the_core_section_is_not_an_unknown_application():
    builder = ConfigurationBuilder(strict=True)
    builder.add_values({"core": {"muted_events": []}})

    builder.build()


def test_the_core_section_rejects_unknown_keys():
    builder = ConfigurationBuilder()
    builder.add_values({"core": {"mute": []}})

    with pytest.raises(ValidationError):
        builder.build()


def test_the_core_section_can_be_set_with_the_set_option():
    builder = ConfigurationBuilder()
    builder.add_values({"core.muted_events": ["a.b"]})

    assert builder.build()["core"].muted_events == ["a.b"]


def test_the_core_section_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("HARP_CORE__MUTED_EVENTS", "a.b, c.d")
    builder = ConfigurationBuilder()
    builder.add_source(EnvVars(prefix="HARP_"))

    assert builder.build()["core"].muted_events == ["a.b", "c.d"]


def test_an_application_cannot_be_named_core():
    with pytest.raises(ValueError, match="core"):
        ApplicationsRegistry().add("harp_apps.core")
