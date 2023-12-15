from dataclasses import asdict

from config.common import Configuration
from rodi import Container
from whistle.protocols import IAsyncEventDispatcher

from harp import get_logger
from harp.contrib.sqlalchemy_storage.settings import SqlAlchemyStorageSettings
from harp.contrib.sqlalchemy_storage.storage import SqlAlchemyStorage
from harp.factories.events import EVENT_FACTORY_BIND
from harp.factories.events.bind import ProxyFactoryBindEvent
from harp.protocols.storage import IStorage

logger = get_logger(__name__)


def register(container: Container, dispatcher: IAsyncEventDispatcher, settings: Configuration):
    logger.info("Registering sqlalchemy_storage ...")

    container.register(SqlAlchemyStorage)
    container.add_alias("storage.sqlalchemy", SqlAlchemyStorage)

    # todo this should be a default in configuration builder, not built configuration
    # maybe not necessary, dataclass should provide good defaults on late binding
    settings._data.setdefault("storage", None)
    if not settings._data["storage"]:
        settings._data["storage"] = asdict(SqlAlchemyStorageSettings())

    # register our late configuration binder (can't be done sooner, because it should only be done if
    # sqlalchemy_storage is used). Not very clean as it needs the plugin to check it itself, but it
    # works for now.
    dispatcher.add_listener(EVENT_FACTORY_BIND, on_bind)


async def on_bind(event: ProxyFactoryBindEvent):
    try:
        storage_type = event.settings.storage.type
    except AttributeError:
        storage_type = None

    if storage_type != "sqlalchemy":
        return

    local_settings = event.settings.bind(SqlAlchemyStorageSettings, "storage")
    event.container.add_instance(local_settings)
    event.container.register(IStorage, SqlAlchemyStorage)
