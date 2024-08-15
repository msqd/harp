from typing import Literal, Union

from pydantic import Field, model_validator

from harp.config import Configurable
from harp_apps.services.settings import DatabaseSettings, RedisSettings


class SqlBlobStorageSettings(Configurable):
    type: Literal["sql"] = "sql"


class RedisBlobStorageSettings(RedisSettings):
    type: Literal["redis"]

    @model_validator(mode="before")
    @classmethod
    def _set_default_type(cls, values):
        values["type"] = "redis"
        return values


class StorageSettings(DatabaseSettings):
    migrate: bool = True
    blobs: Union[SqlBlobStorageSettings, RedisBlobStorageSettings] = Field(
        default_factory=SqlBlobStorageSettings, discriminator="type"
    )
