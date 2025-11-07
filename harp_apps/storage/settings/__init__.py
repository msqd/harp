from typing import Optional

from harp.config import ApplicationSettingsMixin

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(ApplicationSettingsMixin, DatabaseSettings):
    migrate: bool = True
    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
