"""
Sweeps are the periodic cleanups of an application (purge what is old, reclaim what is unused).

An application *declares* its sweeps, at bind or bound, in the :class:`SweepRegistry`. Something else *schedules* them:
the janitor application does, and knows none of the applications that declare. Without a scheduler, nothing runs and
startup warns.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class SweepBudget:
    """
    What one run of a sweep may spend. A limit left to ``None`` is not enforced.

    The scheduler enforces ``seconds`` (a run exceeding it is cancelled and counted as a failure). ``items`` is for the
    sweep function to honour: it is handed the budget, and stops after that many items.
    """

    #: Maximum duration of one run.
    seconds: float | None = None

    #: Maximum number of items (rows, entries, blobs...) one run may handle.
    items: int | None = None

    def __post_init__(self):
        if self.seconds is not None and self.seconds <= 0:
            raise ValueError("A sweep time budget must be positive.")
        if self.items is not None and self.items <= 0:
            raise ValueError("A sweep item budget must be positive.")


#: A sweep function receives its budget, and returns how many items it handled (``None`` when it does not count).
SweepFunction = Callable[[SweepBudget], Awaitable[int | None]]


@dataclass(frozen=True)
class Sweep:
    """A periodic cleanup declared by an application."""

    #: Unique name, namespaced by the declaring application (``storage.transactions``).
    name: str

    #: Minimum time between two runs. ``None`` runs the sweep on every pass of the scheduler.
    interval: timedelta | None

    #: What one run may spend.
    budget: SweepBudget

    #: The work.
    run: SweepFunction

    def __post_init__(self):
        if not self.name:
            raise ValueError("A sweep needs a name.")
        if self.interval is not None and self.interval <= timedelta(0):
            raise ValueError(f"Sweep {self.name!r}: the interval must be positive.")


class SweepRegistry:
    """Where applications declare their sweeps, and a scheduler picks them up."""

    def __init__(self):
        self._sweeps: dict[str, Sweep] = {}
        self._scheduled = False

    def declare(self, sweep: Sweep) -> Sweep:
        if sweep.name in self._sweeps:
            raise ValueError(f"A sweep named {sweep.name!r} is already declared.")
        self._sweeps[sweep.name] = sweep
        return sweep

    def __iter__(self):
        return iter(list(self._sweeps.values()))

    def __len__(self):
        return len(self._sweeps)

    def mark_scheduled(self):
        """Called by the scheduler: from now on, declared sweeps do run."""
        self._scheduled = True

    @property
    def unscheduled(self) -> list[str]:
        """Names of the declared sweeps that will not run because nothing schedules them."""
        return [] if self._scheduled else list(self._sweeps)
