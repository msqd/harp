from dataclasses import dataclass

from harp.services.storage.base import BaseStorageSettings, Storage


class SqlDatabaseStorage(Storage):
    def __init__(self, database):
        self._database = database

    def save(self, entity):
        self._database.session.add(entity)
        self._database.session.commit()

    def select(self, entity_type):
        return self._database.session.query(entity_type).all()

    def count(self, entity_type):
        return self._database.session.query(entity_type).count()


@dataclass(frozen=True)
class SqlDatabaseStorageSettings(BaseStorageSettings):
    type: str = "sql_database"
