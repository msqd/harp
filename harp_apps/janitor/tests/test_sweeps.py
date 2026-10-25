"""The janitor schedules whatever sweeps applications declare, and knows none of them."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest

from harp.sweeps import Sweep, SweepBudget, SweepRegistry
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.worker import JanitorWorker


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


@pytest.fixture
def sweeps() -> SweepRegistry:
    return SweepRegistry()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def worker(sweeps, clock) -> JanitorWorker:
    storage = SimpleNamespace(session_factory=None)
    worker = JanitorWorker(storage, SimpleNamespace(type="none"), JanitorSettings(), sweeps=sweeps)
    worker.clock = clock
    return worker


class Recorder:
    """A sweep function that records its calls."""

    def __init__(self, items=1, error=None, delay=0.0):
        self.budgets = []
        self.items = items
        self.error = error
        self.delay = delay

    async def __call__(self, budget: SweepBudget):
        self.budgets.append(budget)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.items

    @property
    def calls(self) -> int:
        return len(self.budgets)


def declare(sweeps, name, run, *, interval=None, budget=SweepBudget()) -> Sweep:
    return sweeps.declare(Sweep(name=name, interval=interval, budget=budget, run=run))


async def test_marks_the_registry_scheduled_so_startup_does_not_warn(worker, sweeps):
    declare(sweeps, "a.one", Recorder())

    worker.schedule()

    assert sweeps.unscheduled == []


async def test_runs_every_declared_sweep(worker, sweeps):
    first, second = Recorder(), Recorder()
    declare(sweeps, "a.first", first)
    declare(sweeps, "b.second", second)

    await worker.run_sweeps()

    assert (first.calls, second.calls) == (1, 1)


async def test_hands_the_sweep_its_budget(worker, sweeps):
    run = Recorder()
    budget = SweepBudget(seconds=5, items=100)
    declare(sweeps, "a.one", run, budget=budget)

    await worker.run_sweeps()

    assert run.budgets == [budget]


async def test_a_sweep_without_interval_runs_on_every_pass(worker, sweeps):
    run = Recorder()
    declare(sweeps, "a.one", run, interval=None)

    await worker.run_sweeps()
    await worker.run_sweeps()

    assert run.calls == 2


async def test_a_sweep_waits_for_its_interval(worker, sweeps, clock):
    run = Recorder()
    declare(sweeps, "a.one", run, interval=timedelta(hours=1))

    await worker.run_sweeps()
    clock.advance(3599)
    await worker.run_sweeps()
    assert run.calls == 1

    clock.advance(1)
    await worker.run_sweeps()
    assert run.calls == 2


async def test_a_sweep_declared_after_the_first_pass_is_picked_up(worker, sweeps):
    await worker.run_sweeps()
    late = Recorder()
    declare(sweeps, "late.one", late)

    await worker.run_sweeps()

    assert late.calls == 1


async def test_measures_duration_items_and_runs(worker, sweeps, clock):
    async def run(budget):
        clock.advance(2.5)
        return 42

    declare(sweeps, "a.one", run)

    await worker.run_sweeps()
    await worker.run_sweeps()

    stats = worker.sweep_stats["a.one"]
    assert stats.runs == 2
    assert stats.items == 84
    assert stats.failures == 0
    assert stats.last_duration == 2.5


async def test_a_sweep_that_does_not_count_adds_no_items(worker, sweeps):
    async def run(budget):
        return None

    declare(sweeps, "a.one", run)

    await worker.run_sweeps()

    assert worker.sweep_stats["a.one"].items == 0


async def test_a_failing_sweep_is_counted_and_the_others_still_run(worker, sweeps):
    failing, after = Recorder(error=RuntimeError("boom")), Recorder()
    declare(sweeps, "a.failing", failing)
    declare(sweeps, "b.after", after)

    await worker.run_sweeps()

    assert after.calls == 1
    stats = worker.sweep_stats["a.failing"]
    assert (stats.runs, stats.failures) == (1, 1)
    assert "boom" in stats.last_error
    assert worker.sweep_stats["b.after"].failures == 0


async def test_a_failing_sweep_runs_again_at_its_next_turn(worker, sweeps, clock):
    failing = Recorder(error=RuntimeError("boom"))
    declare(sweeps, "a.failing", failing, interval=timedelta(minutes=1))

    await worker.run_sweeps()
    clock.advance(60)
    await worker.run_sweeps()

    assert failing.calls == 2


async def test_a_sweep_over_its_time_budget_is_cancelled_and_counted_as_failed(worker, sweeps):
    slow, after = Recorder(delay=5), Recorder()
    declare(sweeps, "a.slow", slow, budget=SweepBudget(seconds=0.01))
    declare(sweeps, "b.after", after)

    await asyncio.wait_for(worker.run_sweeps(), timeout=2)

    assert after.calls == 1
    stats = worker.sweep_stats["a.slow"]
    assert stats.failures == 1
    assert "time budget" in stats.last_error


async def test_a_success_clears_the_last_error(worker, sweeps, clock):
    run = Recorder(error=RuntimeError("boom"))
    declare(sweeps, "a.one", run)
    await worker.run_sweeps()

    run.error = None
    await worker.run_sweeps()

    assert worker.sweep_stats["a.one"].last_error is None


async def test_loop_runs_the_declared_sweeps(worker, sweeps, monkeypatch):
    run = Recorder()
    declare(sweeps, "a.one", run)

    async def nothing():
        pass

    monkeypatch.setattr(worker, "delete_orphan_blobs", nothing)
    monkeypatch.setattr(worker, "compute_and_store_metrics", nothing)

    await worker.loop()

    assert run.calls == 1
