from collections import deque
from dataclasses import dataclass

from harp.services.storage.base import BaseStorageSettings

from .base import Storage


@dataclass(frozen=True)
class InMemoryStorageSettings(BaseStorageSettings):
    type: str = "in_memory"
    max_size: dict = 1000


class InMemoryDatabase:
    def __init__(self, *, max_size=InMemoryStorageSettings.max_size):
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
        self._database = self.DatabaseType(max_size=self._settings.max_size)

    def save(self, entity):
        self._database.append(entity)

    def select(self, entity_type):
        return self._database._entities

    def count(self, entity_type):
        return len(self._database._entities)
