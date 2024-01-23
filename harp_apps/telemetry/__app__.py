"""
SqlAlchemy Storage Extension

"""
import hashlib
import platform
import sys

from httpx import AsyncClient, TimeoutException

from harp import __version__, get_logger
from harp.config import Application
from harp.config.events import FactoryBoundEvent
from harp.typing import GlobalSettings

logger = get_logger(__name__)


class TelemetryApplication(Application):
    ACTIVITY_ENDPOINT = "https://connect.makersquad.fr/t/a"

    def __init__(self, settings, /):
        super().__init__(settings)

        self._platform = " ".join((platform.python_implementation(), sys.version, "on", platform.platform()))
        self._host = "; ".join(platform.uname())
        self._hashed = hashlib.sha1("\n".join([self._platform, self._host]).encode("utf-8")).hexdigest()

    async def on_bound(self, event: FactoryBoundEvent):
        settings = event.provider.get(GlobalSettings)
        client = event.provider.get(AsyncClient)
        try:
            await client.post(
                type(self).ACTIVITY_ENDPOINT,
                json={
                    "f": self._hashed,
                    "a": ",".join(map(lambda x: x.split(".")[-1], settings["applications"])),
                    "v": __version__,
                    "c": 1,
                },
                timeout=2.0,
            )
        except TimeoutException:
            pass
