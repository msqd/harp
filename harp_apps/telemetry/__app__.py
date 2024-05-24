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
    def __init__(self, settings=None, /):
        super().__init__(settings)

        # keep a reference for application garbage collection (later)
        self.manager = None

    async def on_bind(self, event: FactoryBindEvent):
        event.container.add_singleton(TelemetryManager)

    async def on_bound(self, event: FactoryBoundEvent):
        self.manager = event.provider.get(TelemetryManager)
