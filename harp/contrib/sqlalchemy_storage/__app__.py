"""
SqlAlchemy Storage Extension

"""

from harp.config import Application
from harp.config.factories.events import FactoryBindEvent
from harp.protocols.storage import IStorage

from .settings import SqlAlchemyStorageSettings
from .storage import SqlAlchemyStorage


class SqlalchemyStorageApplication(Application):
    settings_namespace = "storage"
    settings_type = SqlAlchemyStorageSettings

    @classmethod
    def supports(cls, settings):
        return settings.get("type", None) == "sqlalchemy"

    @classmethod
    def defaults(cls, settings=None):
        settings = settings if settings is not None else {"type": "sqlalchemy"}

        if cls.supports(settings):
            settings.setdefault("url", "sqlite+aiosqlite:///:memory:")
            settings.setdefault("echo", False)
            settings.setdefault("drop_tables", False)

        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.register(SqlAlchemyStorage)
        event.container.add_alias("storage.sqlalchemy", SqlAlchemyStorage)
        event.container.add_instance(self.settings)
        event.container.register(IStorage, SqlAlchemyStorage)
