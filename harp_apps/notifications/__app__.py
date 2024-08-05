"""
Notifications Application
"""

from harp import get_logger
from harp.config import Application
from harp_apps.notifications.settings import NotificationsSettings

logger = get_logger(__name__)


application = Application(
    settings_type=NotificationsSettings,
)
