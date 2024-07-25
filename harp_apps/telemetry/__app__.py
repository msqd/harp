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
from harp.config.events import OnBindEvent, OnBoundEvent
from harp_apps.telemetry.manager import TelemetryManager

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    event.container.add_singleton(TelemetryManager)


async def on_bound(event: OnBoundEvent):
    event.provider.get(TelemetryManager)


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
)
