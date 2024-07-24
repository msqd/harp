"""
Telemetry application.

Sends anonymous usage statistics on startup.

todo:
- send ping every 24 hours
- send ping on exit ?
- activity type
- license key
- send platform to allow to understand target env types (linux, windows, macos, what python, etc.)
- detect if within container ?
- detect if within kubernetes ?
- detect git/docker/pip/brew install ?

"""

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent
from harp_apps.telemetry.manager import TelemetryManager

logger = get_logger(__name__)


class TelemetryApplication(Application):
    class Lifecycle:
        @staticmethod
        async def on_bind(event: FactoryBindEvent):
            event.container.add_singleton(TelemetryManager)

        @staticmethod
        async def on_bound(event: FactoryBoundEvent):
            event.provider.get(TelemetryManager)
