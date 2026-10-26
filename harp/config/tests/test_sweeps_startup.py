"""Applications declare sweeps at bind or bound; startup warns when nothing will schedule them."""

import logging

import pytest

from harp.config import Application, ApplicationsRegistry
from harp.config.builders.system import SystemBuilder
from harp.sweeps import Sweep, SweepBudget, SweepRegistry
from harp.typedefs import GlobalSettings


async def noop(budget):
    return 0


def sweep(name: str) -> Sweep:
    return Sweep(name=name, interval=None, budget=SweepBudget(), run=noop)


async def declare_at_bind(event):
    event.sweeps.declare(sweep("bind.sweep"))


async def declare_at_bound(event):
    event.sweeps.declare(sweep("bound.sweep"))


async def schedule(event):
    event.sweeps.mark_scheduled()


async def build(*applications: Application) -> tuple:
    registry = ApplicationsRegistry()
    registry._applications = {f"app{i}": application for i, application in enumerate(applications)}
    system = await SystemBuilder(registry, GlobalSettings(applications={})).abuild(validate_dependencies=False)
    return system, system.provider.get(SweepRegistry)


def sweep_warnings(caplog) -> list[str]:
    return [
        r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and "sweep" in r.getMessage().lower()
    ]


async def test_sweeps_declared_at_bind_and_at_bound_reach_the_registry():
    system, sweeps = await build(Application(on_bind=declare_at_bind, on_bound=declare_at_bound))

    assert [s.name for s in sweeps] == ["bind.sweep", "bound.sweep"]
    await system.dispose()


async def test_declared_sweeps_without_a_scheduler_are_named_in_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        system, _ = await build(Application(on_bind=declare_at_bind, on_bound=declare_at_bound))
    await system.dispose()

    (message,) = sweep_warnings(caplog)
    assert "bind.sweep" in message
    assert "bound.sweep" in message


async def test_no_warning_when_a_scheduler_takes_the_sweeps(caplog):
    with caplog.at_level(logging.WARNING):
        system, _ = await build(Application(on_bind=declare_at_bind), Application(on_bound=schedule))
    await system.dispose()

    assert sweep_warnings(caplog) == []


async def test_no_warning_when_nothing_is_declared(caplog):
    with caplog.at_level(logging.WARNING):
        system, _ = await build(Application())
    await system.dispose()

    assert sweep_warnings(caplog) == []


@pytest.mark.parametrize("hook", ["on_bind", "on_bound"])
async def test_a_scheduler_may_run_before_or_after_the_declaring_application(caplog, hook):
    declaring = Application(on_bound=declare_at_bound)
    scheduler = Application(**{hook: schedule})

    with caplog.at_level(logging.WARNING):
        system, _ = await build(*(declaring, scheduler) if hook == "on_bind" else (scheduler, declaring))
    await system.dispose()

    assert sweep_warnings(caplog) == []
