import rodi

from harp.services.storage import BaseStorageSettings, Storage


def create_container(config):
    container = rodi.Container()

    storage = config.bind(BaseStorageSettings.build, "storage")

    if storage.type == "memory":
        from harp.services.storage.in_memory import InMemoryStorage, InMemoryStorageSettings

        container.add_instance(config.bind(InMemoryStorageSettings, "storage"))
        container.add_singleton(Storage, InMemoryStorage)
    elif storage.type == "database":
        from harp.services.storage.sql_database import SqlDatabaseStorage, SqlDatabaseStorageSettings

        container.add_instance(config.bind(SqlDatabaseStorageSettings, "storage"))
        container.add_singleton(Storage, SqlDatabaseStorage)
    else:
        raise ValueError(f"Invalid storage type: {storage.type}")

    return container
