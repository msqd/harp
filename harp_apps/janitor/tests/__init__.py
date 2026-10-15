from datetime import timedelta

from harp_apps.janitor.worker import JanitorWorker


def worker_with_grace(storage, blob_storage, settings, grace: timedelta) -> JanitorWorker:
    """A worker whose orphan grace period is set, as freshly written blobs are otherwise kept."""
    worker = JanitorWorker(storage, blob_storage, settings)
    worker.orphan_grace = grace
    return worker
