from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import islice
from weakref import WeakValueDictionary

from harp.services.storage.base import BaseStorageSettings

from .base import Storage


@dataclass(frozen=True)
class InMemoryStorageSettings(BaseStorageSettings):
    type: str = "memory"
    max_size: int = 1000


class InMemoryDatabase:
    CollectionType = deque
    IndexType = WeakValueDictionary

    def __init__(self, *, max_size=InMemoryStorageSettings.max_size):
        self._entities = defaultdict(self.CollectionType)
        self._indexes = defaultdict(self.IndexType)
        self._max_size = max_size

    def add(self, entity):
        name = type(entity).__name__
        collection = self._entities[name]
        collection.append(entity)
        if len(collection) > self._max_size:
            collection.popleft()
        self._indexes[name][entity.id] = entity

        for child in entity.children():
            self.add(child)


class InMemoryStorage(Storage):
    DatabaseType = InMemoryDatabase

    def __init__(self, settings: InMemoryStorageSettings = None):
        self._settings = settings or InMemoryStorageSettings()
        self._database = self.DatabaseType(max_size=self._settings.max_size)

    def save(self, entity):
        self._database.add(entity)

    def find(self, entity_type, id):
        return self._database._indexes[entity_type.__name__][id]

    def select(self, entity_type, *, limit=100):
        return islice(reversed(self._database._entities[entity_type.__name__]), None, limit)

    def count(self, entity_type):
        return len(self._database._entities[entity_type.__name__])
