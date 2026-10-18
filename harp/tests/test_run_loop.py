import asyncio
import sys

import pytest
import structlog.testing

import harp


@pytest.fixture
def recorded_run(monkeypatch):
    calls = []

    def fake_run(coro, **kwargs):
        coro.close()
        calls.append(kwargs)

    monkeypatch.setattr(asyncio, "run", fake_run)
    return calls


@pytest.mark.parametrize("server", ["hypercorn+uvloop", "uvicorn"])
def test_without_uvloop_the_asyncio_loop_is_used_with_one_warning(monkeypatch, recorded_run, server):
    monkeypatch.setitem(sys.modules, "uvloop", None)

    with structlog.testing.capture_logs() as logs:
        harp.run(object(), server=server)

    assert recorded_run == [{"loop_factory": None}]
    warnings = [log for log in logs if log["log_level"] == "warning"]
    assert len(warnings) == 1
    assert server in warnings[0]["event"] and sys.platform in warnings[0]["event"]


def test_with_uvloop_its_loop_is_used(recorded_run):
    uvloop = pytest.importorskip("uvloop")

    harp.run(object(), server="hypercorn+uvloop")

    assert recorded_run == [{"loop_factory": uvloop.new_event_loop}]


def test_servers_not_needing_uvloop_get_the_default_loop(recorded_run):
    harp.run(object(), server="granian")

    assert recorded_run == [{}]
