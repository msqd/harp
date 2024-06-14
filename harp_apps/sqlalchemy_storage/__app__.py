"""
SqlAlchemy Storage Extension

"""

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent
from harp.typing.storage import Storage

from .settings import SqlAlchemyStorageSettings
from .storage import SqlAlchemyStorage

logger = get_logger(__name__)


class SqlalchemyStorageApplication(Application):
    settings_namespace = "storage"
    settings_type = SqlAlchemyStorageSettings

    @classmethod
    def supports(cls, settings):
        return settings.get("type", None) == "sqlalchemy"

    @classmethod
    def defaults(cls, settings=None):
        settings = settings if settings is not None else {"type": "sqlalchemy"}

        if cls.supports({"type": "sqlalchemy"} | settings):
            settings.setdefault("type", "sqlalchemy")
            settings.setdefault("url", "sqlite+aiosqlite:///:memory:")
            settings.setdefault("migrate", True)

        return settings

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(Storage, SqlAlchemyStorage)
