from .base import Storage


class InMemoryDatabase:
    def __init__(self):
        self._entities = []

    def append(self, entity):
        self._entities.append(entity)


class InMemoryStorage(Storage):
    def __init__(self, database: InMemoryDatabase):
        self._database = database

    def save(self, entity):
        self._database.append(entity)

    def select(self, entity_type):
        return self._database._entities
