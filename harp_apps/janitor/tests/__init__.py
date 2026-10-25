from datetime import timedelta

from harp.sweeps import SweepBudget
from harp_apps.janitor.settings import JanitorSettings
from harp_apps.janitor.worker import JanitorWorker
from harp_apps.storage.sweeps import transactions_purge_sweep


def worker_with_grace(storage, blob_storage, settings, grace: timedelta) -> JanitorWorker:
    """A worker whose orphan grace period is set, as freshly written blobs are otherwise kept."""
    worker = JanitorWorker(storage, blob_storage, settings)
    worker.orphan_grace = grace
    return worker


async def purge_old_transactions(storage, settings: JanitorSettings) -> int:
    """Run the transaction purge that storage declares as a sweep, with the retention these settings give."""
    return await transactions_purge_sweep(storage, lambda: settings.old_after_delta).run(SweepBudget())
