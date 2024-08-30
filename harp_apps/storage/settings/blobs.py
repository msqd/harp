from typing import Literal

from harp.config import Service


class BlobStorageSettings(Service):
    type: Literal["sql", "redis"] = "sql"
