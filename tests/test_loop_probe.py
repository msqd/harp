import asyncio
import gc
import json

import pytest

from harp.utils import loop_probe


@pytest.fixture(autouse=True)
def no_probe():
    loop_probe.stop()
    yield
    loop_probe.stop()


async def test_off_without_the_variable(monkeypatch):
    monkeypatch.delenv(loop_probe.ENV, raising=False)
    callbacks = list(gc.callbacks)

    assert loop_probe.start_from_environment() is None
    assert loop_probe.current() is None
    assert gc.callbacks == callbacks


async def test_records_lag_gc_and_flushes(monkeypatch, tmp_path):
    path = tmp_path / "probe.jsonl"
    monkeypatch.setenv(loop_probe.ENV, str(path))
    probe = loop_probe.start_from_environment()
    assert loop_probe.current() is probe

    await asyncio.sleep(0.05)
    import time

    time.sleep(0.03)  # blocks the loop: the timer runs late
    await asyncio.sleep(0.02)
    gc.collect()
    probe.flush(tick_at=1.0, started=1.002, wall=0.004, cpu=0.003, transactions=40, open=2, messages=80, blobs=60)
    loop_probe.stop()

    lines = [json.loads(line) for line in path.read_text().splitlines()]
    meta, events = lines[0], lines[1:]
    assert meta["k"] == "meta" and sum(meta["histogram"]) > 10
    assert any(e["k"] == "lag" and e["ms"] > 20 for e in events)
    assert any(e["k"] == "gc" and e["gen"] == 2 for e in events)
    (flush,) = [e for e in events if e["k"] == "flush"]
    assert (flush["transactions"], flush["wait_ms"], flush["ms"]) == (40, 2.0, 4.0)
    assert probe._on_gc not in gc.callbacks
    assert loop_probe.current() is None
