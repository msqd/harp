from collections import defaultdict, deque
from dataclasses import dataclass

from harp.services.storage.base import BaseStorageSettings

from .base import Storage


@dataclass(frozen=True)
class InMemoryStorageSettings(BaseStorageSettings):
    type: str = "memory"
    max_size: int = 1000


class InMemoryDatabase:
    CollectionType = deque

    def __init__(self, *, max_size=InMemoryStorageSettings.max_size):
        self._entities = defaultdict(self.CollectionType)
        self._max_size = max_size

    def append(self, entity):
        collection = self._entities[type(entity).__name__]

        collection.append(entity)
        if len(collection) > self._max_size:
            collection.popleft()


class InMemoryStorage(Storage):
    DatabaseType = InMemoryDatabase

    def __init__(self, settings: InMemoryStorageSettings = None):
        self._settings = settings or InMemoryStorageSettings()
        self._database = self.DatabaseType(max_size=self._settings.max_size)

    def save(self, entity):
        self._database.append(entity)

    def select(self, entity_type):
        return self._database._entities[entity_type.__name__]

    def count(self, entity_type):
        return len(self._database._entities[entity_type.__name__])
