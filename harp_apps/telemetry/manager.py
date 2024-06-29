import asyncio
import hashlib
import platform
import sys
from functools import cached_property

from httpx import AsyncClient, TransportError
from whistle import IAsyncEventDispatcher

from harp import __version__, get_logger
from harp.asgi.events import EVENT_CORE_STARTED
from harp.typing import GlobalSettings
from harp_apps.storage.types import IStorage

logger = get_logger(__name__)


class TelemetryManager:
    default_period = 86400  # 24 hours
    default_endpoint = "https://connect.makersquad.fr/t/a"

    def __init__(
        self,
        global_settings: GlobalSettings,
        client: AsyncClient,
        storage: IStorage = None,
        dispatcher: IAsyncEventDispatcher = None,
        **kwargs,
    ):
        self.global_settings = global_settings
        self.client = client
        self.storage = storage
        self.endpoint = kwargs.pop("endpoint", None) or self.default_endpoint

        self.worker = None
        self.count = 0

        self._platform = " ".join((platform.python_implementation(), sys.version, "on", platform.platform()))
        self._host = "; ".join(platform.uname())
        self._hashed = hashlib.sha1("\n".join([self._platform, self._host]).encode("utf-8")).hexdigest()

        if dispatcher:
            dispatcher.add_listener(EVENT_CORE_STARTED, self.start, priority=-10)

    @cached_property
    def period(self):
        return self.default_period

    @cached_property
    def applications(self):
        return ",".join(map(lambda x: x.split(".")[-1], self.global_settings.get("applications", [])))

    async def start(self, event):
        self.worker = asyncio.create_task(self.loop_forever())

    async def ping(self):
        try:
            return await self.client.post(
                self.endpoint,
                json={
                    # anonymous fingerprint of instance
                    "f": self._hashed,
                    # configured applications
                    "a": self.applications,
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

    async def loop_forever(self):
        while True:
            try:
                await self.ping()
            except TransportError as exc:
                logger.warning("Failed to send activity ping: %s", exc)

            await asyncio.sleep(self.period)
