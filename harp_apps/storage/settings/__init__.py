from typing import Optional

from harp.config import ApplicationSettingsMixin

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(ApplicationSettingsMixin, DatabaseSettings):
    migrate: bool = True
    #: Seconds a transaction may stay open before it is inserted (it is otherwise written once, when it ends).
    early_insert_after: float = 1.0
    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
