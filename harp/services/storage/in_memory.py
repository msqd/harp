from collections import deque
from dataclasses import dataclass, field

from harp.services.storage.base import BaseStorageSettings

from .base import Storage

IN_MEMORY_DATABASE_DEFAULTS = {
    "max_size": 1000,
}


@dataclass(frozen=True)
class InMemoryStorageSettings(BaseStorageSettings):
    type: str = "in_memory"
    database: dict = field(default_factory=lambda: IN_MEMORY_DATABASE_DEFAULTS)


class InMemoryDatabase:
    def __init__(self, *, max_size=IN_MEMORY_DATABASE_DEFAULTS["max_size"]):
        self._entities = deque()
        self._max_size = max_size

    def append(self, entity):
        self._entities.append(entity)
        if self._entities.__len__() > self._max_size:
            self._entities.popleft()


class InMemoryStorage(Storage):
    DatabaseType = InMemoryDatabase

    def __init__(self, settings: InMemoryStorageSettings = None):
        self._settings = settings or InMemoryStorageSettings()
        self._database = self.DatabaseType(**self._settings.database)

    def save(self, entity):
        self._database.append(entity)

    def select(self, entity_type):
        return self._database._entities

    def count(self, entity_type):
        return len(self._database._entities)
