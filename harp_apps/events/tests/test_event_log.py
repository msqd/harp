import pytest
from structlog.testing import capture_logs
from whistle import AsyncEventDispatcher, Event, IAsyncEventDispatcher

from harp._logging import logging_config
from harp.config import ConfigurationBuilder
from harp.config.builders.system import SystemBuilder
from harp.config.defaults import DEFAULT_APPLICATIONS
from harp.unit_of_work import auditable, loggable
from harp_apps.events.__app__ import on_bound
from harp_apps.events.listener import EVENTS_LOGGER
from harp_apps.events.settings import EventsSettings


@loggable("test.events.breaker_opened")
class BreakerOpened(Event):
    details_fields = ("remote",)

    def __init__(self, remote="a", **extra):
        super().__init__()
        self.outcome = "failed"
        self.details = {"remote": remote, **extra}


@loggable("test.events.sign_in_failed")
class SignInFailed(Event):
    pass


@auditable("test.events.audited")
class Audited(Event):
    pass


class Unmarked(Event):
    event_id = "test.events.breaker_opened"  # would be loggable, were the mark not required


class FakeProvider:
    def __init__(self, dispatcher, settings):
        self._services = {IAsyncEventDispatcher: dispatcher, EventsSettings: settings}

    def get(self, key):
        return self._services[key]


class Bound:
    def __init__(self, dispatcher, settings):
        self.provider = FakeProvider(dispatcher, settings)


async def bound(*, muted=()):
    dispatcher = AsyncEventDispatcher()
    await on_bound(Bound(dispatcher, EventsSettings(muted=list(muted))))
    return dispatcher


def test_events_is_a_default_application():
    assert "events" in DEFAULT_APPLICATIONS


def test_lines_go_to_the_harp_events_logger_which_has_its_own_level():
    assert EVENTS_LOGGER == "harp.events"
    assert logging_config["loggers"]["harp.events"]["level"] == "INFO"


def test_settings_default_to_muting_nothing():
    assert EventsSettings().muted == []


async def test_a_loggable_event_is_written_as_one_structured_line():
    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.events.breaker_opened", BreakerOpened(remote="upstream"))

    assert len(logs) == 1
    assert logs[0]["kind"] == "event"
    assert logs[0]["event_id"] == "test.events.breaker_opened"
    assert logs[0]["outcome"] == "failed"
    assert logs[0]["details"] == {"remote": "upstream"}
    assert logs[0]["log_level"] == "info"


async def test_only_declared_scalar_details_are_logged():
    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch(
            "test.events.breaker_opened", BreakerOpened(remote="upstream", extra="x", other={"nested": 1})
        )

    assert logs[0]["details"] == {"remote": "upstream"}


async def test_an_event_without_details_is_logged_bare():
    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.events.sign_in_failed", SignInFailed())

    assert logs[0]["event_id"] == "test.events.sign_in_failed"
    assert logs[0]["details"] == {}


async def test_a_muted_event_is_not_logged():
    dispatcher = await bound(muted=["test.events.breaker_opened"])

    with capture_logs() as logs:
        await dispatcher.adispatch("test.events.breaker_opened", BreakerOpened())
        await dispatcher.adispatch("test.events.sign_in_failed", SignInFailed())

    assert [log["event_id"] for log in logs] == ["test.events.sign_in_failed"]


@pytest.mark.parametrize("event_id", ["proxy.transaction.started", "test.events.audited", "test.events.unknown"])
async def test_muting_what_is_not_loggable_fails_validation(event_id):
    with pytest.raises(ValueError, match=event_id):
        await bound(muted=[event_id])


@pytest.mark.parametrize(
    "event_id,event", [("proxy.transaction.started", Unmarked()), ("test.events.audited", Audited())]
)
async def test_an_event_that_is_not_loggable_is_never_logged(event_id, event):
    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch(event_id, event)

    assert logs == []


async def test_an_unmarked_event_dispatched_under_a_loggable_id_is_never_logged():
    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.events.breaker_opened", Unmarked())

    assert logs == []


async def test_a_line_that_cannot_be_built_does_not_break_the_dispatch():
    class Broken(BreakerOpened):
        @property
        def details(self):
            raise RuntimeError("cannot build")

        @details.setter
        def details(self, value):
            pass

    dispatcher = await bound()

    with capture_logs() as logs:
        await dispatcher.adispatch("test.events.breaker_opened", Broken())

    assert logs == []


async def test_muting_is_validated_when_the_system_is_built():
    builder = ConfigurationBuilder()
    builder.add_values({"events": {"muted": ["proxy.transaction.started"]}})

    with pytest.raises(ValueError, match="proxy.transaction.started"):
        await SystemBuilder(builder.applications, builder.build()).abuild()
