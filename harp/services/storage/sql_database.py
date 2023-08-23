from dataclasses import dataclass

from sqlalchemy import Column, MetaData, String, Table, create_engine

from harp.services.storage.base import BaseStorageSettings, Storage


@dataclass(frozen=True)
class SqlDatabaseStorageSettings(BaseStorageSettings):
    type: str = "sql_database"
    name: str = "harp"
    user: str = "postgres"
    password: str = ""
    host: str = "localhost"
    port: int = 5432

    def get_connection_string(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


meta = MetaData()


class tables:
    transactions = Table(
        "transactions",
        meta,
        Column("name", String(50), primary_key=True),
    )


class SqlDatabaseStorage(Storage):
    def __init__(self, settings: SqlDatabaseStorageSettings):
        self._settings = settings

        self._engine = create_engine(self._settings.get_connection_string(), echo=True)

        from sqlalchemy_utils import create_database, database_exists

        if not database_exists(self._engine.url):
            create_database(self._engine.url)

        with self._engine.connect() as connection:
            meta.create_all(connection)

    def save(self, entity):
        print(entity)
        pass

    def select(self, entity_type):
        return []

    def count(self, entity_type):
        return 0
