import sys

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from harp_apps.contrib.sentry.__app__ import init_sentry

PASSWORD = "s3cr3t-passw0rd"


class SinkTransport(Transport):
    """Local Sentry sink, keeps every event it is asked to send."""

    def __init__(self, options=None):
        super().__init__(options)
        self.events = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.headers.get("type") == "event":
                self.events.append(item.payload.json)


@pytest.fixture
def sink():
    transport = SinkTransport()
    yield transport
    sentry_sdk.get_client().close()


def test_events_carry_no_command_line_secret(sink, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["harp", "start", "--set", f"storage.url=postgresql://u:{PASSWORD}@db/harp"])
    init_sentry("https://key@sentry.invalid/1", transport=sink)

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        sentry_sdk.capture_exception(exc)
    sentry_sdk.flush()

    assert len(sink.events) == 1
    assert PASSWORD not in repr(sink.events)


def test_events_carry_no_secret_held_in_a_local_variable(sink):
    init_sentry("https://key@sentry.invalid/1", transport=sink)

    def connect():
        url = f"postgresql://u:{PASSWORD}@db/harp"  # noqa: F841
        raise RuntimeError("connection failed")

    try:
        connect()
    except RuntimeError as exc:
        sentry_sdk.capture_exception(exc)
    sentry_sdk.flush()

    assert len(sink.events) == 1
    assert PASSWORD not in repr(sink.events)
