from typing import Optional

from harp.config import ApplicationSettingsMixin

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(ApplicationSettingsMixin, DatabaseSettings):
    migrate: bool = True
    #: Seconds a transaction may stay open before it is inserted (it is otherwise written once, when it ends). Checked
    #: at each flush, so it is met within ``flush_interval``.
    early_insert_after: float = 1.0
    #: Seconds after which a transaction that never ended is forgotten by the worker.
    pending_max_age: float = 3600.0
    #: Ended transactions are written together, every this many seconds...
    flush_interval: float = 1.0
    #: ...or as soon as this many have ended, whichever comes first.
    flush_batch_size: int = 500
    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
