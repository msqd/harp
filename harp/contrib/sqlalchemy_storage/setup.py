from config.common import Configuration
from rodi import Container
from whistle import EventDispatcher

from harp import get_logger
from harp.contrib.sqlalchemy_storage.events import on_transaction_ended, on_transaction_message, on_transaction_started
from harp.core.asgi.events import (
    EVENT_CORE_STARTED,
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
)

logger = get_logger(__name__)


def register(container: Container, dispatcher: EventDispatcher, settings: Configuration):
    logger.info("Registering sqlalchemy_storage ...")

    print(settings.values)

    from harp.contrib.sqlalchemy_storage.events import on_startup  # , on_transaction_ended, on_transaction_started

    dispatcher.add_listener(EVENT_CORE_STARTED, on_startup, priority=-20)
    dispatcher.add_listener(EVENT_TRANSACTION_STARTED, on_transaction_started)
    dispatcher.add_listener(EVENT_TRANSACTION_ENDED, on_transaction_ended)
    dispatcher.add_listener(EVENT_TRANSACTION_MESSAGE, on_transaction_message)
