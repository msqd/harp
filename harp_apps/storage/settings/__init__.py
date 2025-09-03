from typing import Optional

from pydantic import Field

from .blobs import BlobStorageSettings
from .database import DatabaseSettings
from .redis import RedisSettings


class StorageSettings(DatabaseSettings):
    migrate: bool = True
    blobs: BlobStorageSettings = BlobStorageSettings()
    redis: Optional[RedisSettings] = None
    skip_storage_requests_payload: list[str] = Field(default_factory=list)
    skip_storage_responses_payload: list[str] = Field(default_factory=list)
