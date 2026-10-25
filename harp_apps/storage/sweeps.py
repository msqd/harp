"""Sweeps declared by the storage application (see :mod:`harp.sweeps`)."""

from collections.abc import Callable
from datetime import timedelta

from harp.sweeps import Sweep, SweepBudget
from harp_apps.storage.services import SqlStorage

TRANSACTIONS_SWEEP = "storage.transactions"


def transactions_purge_sweep(storage: SqlStorage, old_after: Callable[[], timedelta]) -> Sweep:
    """
    Remove transactions older than the retention period, except flagged ones. The database cascades the deletion to
    messages and tag values; their blobs are then freed by the janitor's orphan sweep.

    :param old_after: gives the retention period, read at each run.
    """

    async def purge(budget: SweepBudget) -> int:
        return await storage.transactions.purge_old(old_after())

    return Sweep(name=TRANSACTIONS_SWEEP, interval=None, budget=SweepBudget(), run=purge)
