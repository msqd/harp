from typing import Optional

from pydantic import Field

from harp.config import ApplicationSettingsMixin

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(ApplicationSettingsMixin, DatabaseSettings):
    migrate: bool = True

    #: Number of days after which transactions are deleted (unless flagged by a user).
    retention_days: int = Field(60, gt=0, description="Age in days after which transactions are deleted.")

    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
