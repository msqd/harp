import os
from dataclasses import asdict

import rodi
from config.common import ConfigurationBuilder, MapSource
from config.env import EnvVars
from config.yaml import YAMLFile

from harp.services.storage import BaseStorageSettings, DefaultStorageSettings, Storage

environment_name = os.environ.get("HARP_ENV", "dev")


def create_config(settings=None):
    builder = ConfigurationBuilder()

    builder.add_source(
        MapSource(
            {
                "storage": asdict(DefaultStorageSettings()),
            }
        )
    )
    builder.add_source(YAMLFile("settings.yaml", optional=True))
    builder.add_source(YAMLFile(f"settings.{environment_name}.yaml", optional=True))
    if settings:
        builder.add_source(MapSource(settings))

    builder.add_source(EnvVars(prefix="HARP_"))

    return builder.build()


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


__all__ = [
    "create_config",
    "create_container",
]
