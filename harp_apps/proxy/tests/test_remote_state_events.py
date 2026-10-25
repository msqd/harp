import asyncio
from contextlib import asynccontextmanager

import pytest
from structlog.testing import capture_logs
from whistle import AsyncEventDispatcher

from harp.config import ConfigurationBuilder
from harp.unit_of_work import UnitOfWork, is_auditable, is_loggable, loggable_events
from harp_apps.proxy.constants import CHECKING, DOWN, UP
from harp_apps.proxy.events import EVENT_REMOTE_STATE_CHANGED, RemoteStateChanged, RemoteStateChangedByHand
from harp_apps.proxy.remote_events import relay_state_changes
from harp_apps.proxy.settings import Proxy
from harp_apps.proxy.settings.remote import Remote

URL = "http://example.com/"


class InMemoryUnitOfWork(UnitOfWork):
    @asynccontextmanager
    async def _transaction(self):
        yield


@pytest.fixture
def dispatcher():
    return AsyncEventDispatcher()


@pytest.fixture
def emitted(dispatcher):
    events = []

    async def collect(event):
        events.append(event)

    dispatcher.add_listener(EVENT_REMOTE_STATE_CHANGED, collect)
    return events


def remote_relayed_to(dispatcher, url=URL, **endpoint_settings) -> Remote:
    remote = Remote.from_settings_dict({"endpoints": [{"url": url, **endpoint_settings}]})
    relay_state_changes(remote, endpoint="api", dispatcher=dispatcher)
    return remote


async def settle():
    await asyncio.sleep(0)
    await asyncio.sleep(0)


def test_the_automatic_event_is_loggable_and_the_manual_one_auditable():
    assert is_loggable(RemoteStateChanged) and not is_auditable(RemoteStateChanged)
    assert is_auditable(RemoteStateChangedByHand) and not is_loggable(RemoteStateChangedByHand)
    assert loggable_events()[EVENT_REMOTE_STATE_CHANGED] is RemoteStateChanged


async def test_a_transition_emits_the_loggable_event_without_actor(dispatcher, emitted):
    remote = remote_relayed_to(dispatcher)

    remote.set_down(URL)
    await settle()

    (event,) = emitted
    assert isinstance(event, RemoteStateChanged)
    assert event.details == {"endpoint": "api", "url": URL, "from": "checking", "to": "down"}
    assert not hasattr(event, "actor")


async def test_repeated_failures_on_a_down_remote_emit_once(dispatcher, emitted):
    remote = remote_relayed_to(dispatcher, liveness={"type": "naive", "failure_threshold": 2})

    for _ in range(5):
        remote[URL].failure("HTTP_503")
    await settle()

    assert [event.details["to"] for event in emitted] == ["down"]


async def test_recovery_by_liveness_emits(dispatcher, emitted):
    remote = remote_relayed_to(dispatcher, liveness={"type": "naive"})
    remote.set_down(URL)

    remote[URL].success()
    await settle()

    assert [(event.details["from"], event.details["to"]) for event in emitted] == [
        ("checking", "down"),
        ("down", "up"),
    ]


async def test_the_url_carries_no_credentials(dispatcher, emitted):
    credentialed = "http://user:hunter2@example.com/"
    remote = remote_relayed_to(dispatcher, url=credentialed)

    remote.set_up(credentialed)
    await settle()

    (event,) = emitted
    assert event.details["url"] == URL


async def test_a_change_made_in_a_unit_of_work_is_left_to_it(dispatcher, emitted):
    remote = remote_relayed_to(dispatcher)

    async with InMemoryUnitOfWork(transactional=AsyncEventDispatcher(), dispatcher=dispatcher):
        remote.set_up(URL)
    await settle()

    assert emitted == []


def test_without_a_running_loop_a_transition_goes_unnoticed_without_failing(dispatcher):
    remote = remote_relayed_to(dispatcher)

    remote.set_up(URL)

    assert remote[URL].status == UP


async def test_the_proxy_application_relays_the_transitions_of_its_remotes_to_the_event_log():
    builder = ConfigurationBuilder(
        {"proxy": {"endpoints": [{"name": "api", "port": 4000, "url": "http://example.com"}]}},
        use_default_applications=False,
    )
    builder.applications.add("http_client", "proxy")
    system = await builder.abuild_system(validate_dependencies=False)
    try:
        (endpoint,) = system.provider.get(Proxy).endpoints

        with capture_logs() as logs:
            endpoint.remote.set_down(URL)
            await settle()
    finally:
        await system.dispose()

    (line,) = [log for log in logs if log.get("kind") == "event"]
    assert line["event_id"] == EVENT_REMOTE_STATE_CHANGED
    assert line["details"] == {"endpoint": "api", "url": URL, "from": "checking", "to": "down"}


@pytest.mark.parametrize(("status", "name"), [(UP, "up"), (DOWN, "down"), (CHECKING, "checking")])
async def test_states_are_named(dispatcher, emitted, status, name):
    remote = remote_relayed_to(dispatcher)
    remote[URL].status = DOWN if status != DOWN else UP

    remote[URL].status = status
    await settle()

    assert emitted[-1].details["to"] == name
