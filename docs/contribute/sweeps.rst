Sweeps
======

.. tags:: applications

A sweep is a periodic cleanup: purge what is old, reclaim what is unused. An application *declares* its sweeps, the
:doc:`janitor </apps/janitor/index>` *schedules* them. The janitor knows none of the applications that declare: the
contract lives in the core, :mod:`harp.sweeps`.

Declaring a sweep
:::::::::::::::::

A :class:`~harp.sweeps.Sweep` has a name, an interval, a budget and an async function.

.. code-block:: python

    from datetime import timedelta

    from harp.config import OnBindEvent
    from harp.sweeps import Sweep, SweepBudget


    async def purge(budget: SweepBudget) -> int:
        """Remove what is expired, at most `budget.items` of it. Return how many were removed."""
        ...


    async def on_bind(event: OnBindEvent):
        event.sweeps.declare(
            Sweep(
                name="myapp.expired",
                interval=timedelta(hours=1),
                budget=SweepBudget(seconds=30, items=10_000),
                run=purge,
            )
        )

Declare at bind (``event.sweeps`` on :class:`~harp.config.OnBindEvent`) or at bound (``event.sweeps`` on
:class:`~harp.config.OnBoundEvent`). Declare at bound when the function needs a live service: close over the provider,
or over the service you just got from it. Declaring is all an application does; it does not import, reach or start
anything of the janitor.

name
    Unique, prefixed by the application (``storage.transactions``). It labels the measures. Declaring two sweeps with
    the same name raises.

interval
    The minimum time between two runs, or ``None`` to run on every pass of the janitor (``janitor.period``). The
    janitor only looks every ``period`` seconds: an interval is rounded up to a multiple of it.

budget
    What one run may spend, :class:`~harp.sweeps.SweepBudget` with ``seconds`` and ``items``, each ``None`` when
    unlimited. The janitor enforces ``seconds``: a run still going after that is cancelled and counted as a failure.
    ``items`` is for your function to honour: it receives the budget, and stops after that many items. A sweep that did
    not finish picks the rest up at its next run.

function
    ``async def run(budget) -> int | None``, returns how many items it handled (``None`` when it does not count).

What the janitor does with it
:::::::::::::::::::::::::::::

Each pass, the janitor runs the declared sweeps that are due, one after the other, and measures each: runs, failures,
items and last duration (``JanitorWorker.sweep_stats``; Prometheus ``janitor_sweep_runs_total``,
``janitor_sweep_failures_total``, ``janitor_sweep_items_total`` and ``janitor_sweep_duration_seconds``, labelled by
sweep). A sweep that raises or runs out of time is logged and counted, and never stops the others nor the janitor.

Without the janitor
:::::::::::::::::::

If the janitor is not loaded (``janitor.enabled: false``), nothing schedules the sweeps and nothing runs them. Startup
logs one warning naming the declared sweeps that will not run. Do not run a sweep of your own as a fallback: the
operator who disabled the janitor chose that.

Testing a sweep
:::::::::::::::

Test the function directly, with a budget: it is a plain coroutine. Test the scheduling through
``JanitorWorker.run_sweeps()`` with a :class:`~harp.sweeps.SweepRegistry` you fill yourself.
