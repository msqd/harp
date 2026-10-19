"""
Opt-in diagnostic: where does the event loop stall, and what was running then.

Off unless ``BENCH_LOOP_PROBE`` names a file: nothing is installed, no hook is called, the only cost is reading the
variable once at startup. On, it records (timestamps are ``time.monotonic()``, shared by every process of the host):

- loop lag: a timer every ``PERIOD`` seconds notes how late it ran; late runs above ``MIN_LAG`` (1.5 ms) are kept, all feed a
  histogram. This is itself a few hundred wakeups per second: compare runs that all have the probe on.
- garbage collections: generation, pause and objects collected, for pauses above ``MIN_GC``.
- flushes of the storage worker: wall time, CPU time, rows, and how long they waited after their tick.

Everything stays in memory and is written as JSON lines when the server stops.
"""

import asyncio
import gc
import json
import os
import time
from bisect import bisect_right
from pathlib import Path
from typing import Optional

ENV = "BENCH_LOOP_PROBE"
PERIOD = 0.002
# Timers fire up to a millisecond late on any loop (the selector's resolution): only a clear overrun is kept.
MIN_LAG = 0.0015
MIN_GC = 0.0001
BUCKETS_MS = (0.25, 0.5, 1, 2, 3, 5, 10, 20, 50, 100)

_current: Optional["LoopProbe"] = None


def current() -> Optional["LoopProbe"]:
    """The running probe, if any: hooks check this once and skip all work when it is None."""
    return _current


class LoopProbe:
    def __init__(self, path: Path):
        self.path = path
        self.events: list[dict] = []
        self.histogram = [0] * (len(BUCKETS_MS) + 1)
        self._started = time.monotonic()
        self._handle: Optional[asyncio.TimerHandle] = None
        self._due = 0.0
        self._gc_start = 0.0

    def start(self) -> None:
        gc.callbacks.append(self._on_gc)
        loop = asyncio.get_running_loop()
        self._due = loop.time() + PERIOD
        self._handle = loop.call_at(self._due, self._tick)

    def _tick(self) -> None:
        loop = asyncio.get_running_loop()
        now = loop.time()
        lag = now - self._due
        self.histogram[bisect_right(BUCKETS_MS, lag * 1000)] += 1
        if lag >= MIN_LAG:
            self.events.append({"k": "lag", "t": time.monotonic(), "ms": round(lag * 1000, 3)})
        self._due = max(self._due + PERIOD, now)
        self._handle = loop.call_at(self._due, self._tick)

    def _on_gc(self, phase: str, info: dict) -> None:
        if phase == "start":
            self._gc_start = time.perf_counter()
            return
        pause = time.perf_counter() - self._gc_start
        if pause >= MIN_GC:
            self.events.append(
                {
                    "k": "gc",
                    "t": time.monotonic(),
                    "gen": info["generation"],
                    "ms": round(pause * 1000, 3),
                    "collected": info["collected"],
                }
            )

    def flush(self, *, tick_at: Optional[float], started: float, wall: float, cpu: float, **rows: int) -> None:
        """One flush of the storage worker: ``started`` and ``tick_at`` are monotonic, ``wall`` and ``cpu`` seconds."""
        self.events.append(
            {
                "k": "flush",
                "t": started,
                "ms": round(wall * 1000, 3),
                "cpu_ms": round(cpu * 1000, 3),
                "wait_ms": round((started - tick_at) * 1000, 3) if tick_at else None,
                **rows,
            }
        )

    def stop(self) -> None:
        if self._handle:
            self._handle.cancel()
            self._handle = None
        if self._on_gc in gc.callbacks:
            gc.callbacks.remove(self._on_gc)
        meta = {
            "k": "meta",
            "start": self._started,
            "end": time.monotonic(),
            "period_ms": PERIOD * 1000,
            "buckets_ms": list(BUCKETS_MS),
            "histogram": self.histogram,
            "gc_threshold": list(gc.get_threshold()),
            "gc_frozen": gc.get_freeze_count(),
            "gc_stats": gc.get_stats(),
        }
        with self.path.open("w") as out:
            for event in (meta, *self.events):
                out.write(json.dumps(event) + "\n")


def start_from_environment() -> Optional[LoopProbe]:
    """Starts the probe if ``BENCH_LOOP_PROBE`` is set. Call from inside the running loop."""
    global _current
    path = os.environ.get(ENV)
    if not path:
        return None
    _current = LoopProbe(Path(path))
    _current.start()
    return _current


def stop() -> None:
    global _current
    if _current:
        _current.stop()
        _current = None
