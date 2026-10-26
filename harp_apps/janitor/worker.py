import asyncio
import time
from dataclasses import dataclass

from prometheus_client import Counter, Gauge

from harp import get_logger
from harp.sweeps import Sweep, SweepRegistry
from .settings import JanitorSettings

logger = get_logger(__name__)

SWEEP_RUNS = Counter("janitor_sweep_runs", "Runs of a declared sweep.", ["sweep"])
SWEEP_FAILURES = Counter(
    "janitor_sweep_failures", "Runs of a declared sweep that failed or ran out of time.", ["sweep"]
)
SWEEP_ITEMS = Counter("janitor_sweep_items", "Items handled by a declared sweep.", ["sweep"])
SWEEP_DURATION = Gauge("janitor_sweep_duration_seconds", "Duration of the last run of a declared sweep.", ["sweep"])


@dataclass
class SweepStats:
    """What the janitor measured about one declared sweep."""

    runs: int = 0
    failures: int = 0
    items: int = 0
    last_duration: float | None = None
    last_error: str | None = None
    last_started: float | None = None


class JanitorWorker:
    def __init__(self, settings: JanitorSettings, sweeps: SweepRegistry = None):
        self.settings = settings

        #: Sweeps declared by applications, the janitor schedules them without knowing who declared what.
        self.sweeps: SweepRegistry = sweeps if sweeps is not None else SweepRegistry()
        self.sweep_stats: dict[str, SweepStats] = {}
        self.clock = time.monotonic

        self.running = False
        self._running_lock = asyncio.Lock()

    def schedule(self):
        """
        Tell the registry that someone schedules the declared sweeps, so startup does not warn they will not run.
        """
        self.sweeps.mark_scheduled()

    def stop(self):
        """
        Mark the loop for termination.
        """
        self.running = False

    async def run(self):
        """
        Once dependencies are ready, start the main loop (basically, run the `loop()` every `period` seconds), until
        `stop()` is called.
        """
        # do not start before storage is ready
        async with self._running_lock:
            self.running = True

            while self.running:
                try:
                    await self.loop()
                except Exception as exc:
                    logger.exception(exc)
                await asyncio.sleep(self.settings.period)

    async def loop(self):
        """
        One iteration of the janitor loop.
        """

        await self.run_sweeps()

    async def run_sweeps(self):
        """
        Run the declared sweeps that are due. A sweep that fails or runs out of time is counted, never stops the others.
        """
        for sweep in self.sweeps:
            stats = self.sweep_stats.setdefault(sweep.name, SweepStats())
            if self._is_due(sweep, stats):
                await self._run_sweep(sweep, stats)

    def _is_due(self, sweep: Sweep, stats: SweepStats) -> bool:
        if sweep.interval is None or stats.last_started is None:
            return True
        return self.clock() - stats.last_started >= sweep.interval.total_seconds()

    async def _run_sweep(self, sweep: Sweep, stats: SweepStats):
        started = stats.last_started = self.clock()
        stats.runs += 1
        SWEEP_RUNS.labels(sweep.name).inc()
        items = 0
        try:
            async with asyncio.timeout(sweep.budget.seconds) as deadline:
                items = await sweep.run(sweep.budget) or 0
        except Exception as exc:
            if deadline.expired():
                self._record_failure(sweep, stats, f"ran out of its time budget ({sweep.budget.seconds}s)")
            else:
                logger.exception(exc)
                self._record_failure(sweep, stats, f"{type(exc).__name__}: {exc}")
        else:
            stats.last_error = None
        stats.items += items
        stats.last_duration = self.clock() - started
        SWEEP_ITEMS.labels(sweep.name).inc(items)
        SWEEP_DURATION.labels(sweep.name).set(stats.last_duration)
        logger.debug("🧹 Sweep %s: %d items in %.3fs", sweep.name, items, stats.last_duration)

    @staticmethod
    def _record_failure(sweep: Sweep, stats: SweepStats, error: str):
        stats.failures += 1
        stats.last_error = error
        SWEEP_FAILURES.labels(sweep.name).inc()
        logger.warning("🧹 Sweep %s failed: %s", sweep.name, error)
