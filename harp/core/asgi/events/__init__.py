from harp import get_logger

logger = get_logger(__name__)


EVENT_CORE_CONTROLLER = "core.controller"
EVENT_CORE_REQUEST = "core.request"
EVENT_CORE_RESPONSE = "core.response"
EVENT_CORE_STARTED = "core.startup"
EVENT_CORE_VIEW = "core.view"
EVENT_TRANSACTION_ENDED = "transaction.ended"
EVENT_TRANSACTION_STARTED = "transaction.started"
EVENT_TRANSACTION_MESSAGE = "transaction.message"
