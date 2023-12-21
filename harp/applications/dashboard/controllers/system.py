import re
from copy import deepcopy

from config.common import Configuration

from harp import __revision__, __version__
from harp.applications.dashboard.settings import DashboardSettings
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views.json import json


def _asdict(obj):
    if isinstance(obj, dict):
        return {k: _asdict(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_asdict(v) for v in obj]

    if isinstance(obj, tuple):
        return tuple(_asdict(v) for v in obj)

    if hasattr(obj, "to_dict"):
        result = _asdict(obj.to_dict())
        if isinstance(result, dict):
            return {"@type": type(obj).__name__, **result}
        return result

    return obj


class SystemController:
    prefix = "/api/system"

    def __init__(
        self,
        settings: Configuration,
    ):
        self.settings = settings

    def register(self, router):
        router.route(self.prefix + "/")(self.get)
        router.route(self.prefix + "/settings")(self.get_settings)

    async def get(self, request: ASGIRequest, response: ASGIResponse):
        try:
            context = request.context
        except AttributeError:
            context = {}

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    async def get_settings(self, request: ASGIRequest, response: ASGIResponse):
        settings = deepcopy(_asdict(self.settings.values))
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])
        return json(settings)


if __name__ == "__main__":
    print(_asdict(DashboardSettings()))
