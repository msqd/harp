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
import hashlib
import platform
import sys

from httpx import AsyncClient, TransportError
from rodi import CannotResolveTypeException

from harp import __version__, get_logger
from harp.config import Application
from harp.config.events import FactoryBoundEvent
from harp.typing import GlobalSettings
from harp.typing.storage import Storage

logger = get_logger(__name__)


class TelemetryApplication(Application):
    default_endpoint = "https://connect.makersquad.fr/t/a"

    def __init__(self, settings=None, /, endpoint=None):
        self.endpoint = endpoint or type(self).default_endpoint

        super().__init__(settings)

        self._platform = " ".join((platform.python_implementation(), sys.version, "on", platform.platform()))
        self._host = "; ".join(platform.uname())
        self._hashed = hashlib.sha1("\n".join([self._platform, self._host]).encode("utf-8")).hexdigest()

        self.count = 0

        self.storage = None

    async def on_bound(self, event: FactoryBoundEvent):
        global_settings = event.provider.get(GlobalSettings)
        applications = ",".join(map(lambda x: x.split(".")[-1], global_settings["applications"]))

        try:
            self.storage = event.provider.get(Storage)
        except CannotResolveTypeException:
            self.storage = None

        try:
            await self.ping(event.provider.get(AsyncClient), applications=applications)
        except TransportError as exc:
            logger.warning("Failed to send activity ping: %s", exc)

    async def ping(self, client, /, *, applications):
        try:
            return await client.post(
                self.endpoint,
                json={
                    # anonymous fingerprint of instance
                    "f": self._hashed,
                    # configured applications
                    "a": applications,
                    # application version
                    "v": __version__,
                    # transaction count in last period (not implemented yet)
                    "c": (await self.storage.get_usage()) if self.storage else 0,
                    # activity type
                    "t": "ping" if self.count else "start",
                    # incrementing counter
                    "i": self.count,
                },
                timeout=5.0,
            )
        finally:
            self.count += 1
