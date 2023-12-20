import re
from copy import deepcopy

from config.common import Configuration

from harp import __revision__, __version__
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views.json import json


class SystemController:
    prefix = "/api/system"

    def __init__(self, settings: Configuration, *, context=None):
        self.settings = settings
        self.context = context if context is not None else {}

    def register(self, router):
        router.route(self.prefix + "/")(self.get)
        router.route(self.prefix + "/settings")(self.get_settings)

    async def get(self, request: ASGIRequest, response: ASGIResponse):
        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": self.context.get("user"),
            }
        )

    async def get_settings(self, request: ASGIRequest, response: ASGIResponse):
        settings = deepcopy(self.settings.values)
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])
        return json(settings)
