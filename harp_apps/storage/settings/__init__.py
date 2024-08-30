from typing import Optional

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(DatabaseSettings):
    migrate: bool = True
    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
