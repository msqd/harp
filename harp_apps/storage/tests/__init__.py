from datetime import timedelta

from harp_apps.storage.sweeps import StorageSweeps

#: Retention used by tests that do not care about it.
RETENTION = timedelta(days=60)


def sweeps_with_grace(storage, blob_storage, grace: timedelta) -> StorageSweeps:
    """Storage sweeps whose orphan grace period is set, as freshly written blobs are otherwise kept."""
    sweeps = StorageSweeps(storage, blob_storage, RETENTION)
    sweeps.orphan_grace = grace
    return sweeps
