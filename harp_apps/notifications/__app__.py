"""
Notifications Application
"""

from harp import get_logger
from harp.config import Application
from harp.config.events import OnBoundEvent, OnShutdownEvent
from harp.services import CannotResolveTypeException
from harp_apps.dashboard.settings import DashboardSettings
from harp_apps.notifications.settings import NotificationsSettings
from harp_apps.notifications.subscriber import NotificationSubscriber

logger = get_logger(__name__)

NOTIFICATIONS_SUBSCRIBER = "notifications.subscriber"


async def on_bound(event: OnBoundEvent):
    notifications_settings = event.provider.get(NotificationsSettings)

    public_url = None
    try:
        dashboard_settings = event.provider.get(DashboardSettings)
        public_url = dashboard_settings.public_url
    except CannotResolveTypeException:
        pass

    subscriber = NotificationSubscriber(notifications_settings, public_url)
    subscriber.subscribe(event.dispatcher)
    event.provider.set(NOTIFICATIONS_SUBSCRIBER, subscriber)


async def on_shutdown(event: OnShutdownEvent):
    subscriber = event.provider.get(NOTIFICATIONS_SUBSCRIBER)
    subscriber.unsubscribe(event.dispatcher)


application = Application(
    on_bound=on_bound,
    on_shutdown=on_shutdown,
    settings_type=NotificationsSettings,
)
