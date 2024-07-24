"""Storage Application"""

from harp import get_logger

from .lifecycle import StorageLifecycle
from .settings import StorageSettings

logger = get_logger(__name__)


class StorageApplication:
    Settings = StorageSettings
    Lifecycle = StorageLifecycle
