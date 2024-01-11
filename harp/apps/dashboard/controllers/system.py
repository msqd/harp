import re
from copy import deepcopy

from harp import __revision__, __version__
from harp.apps.dashboard.utils.dependencies import get_python_dependencies, parse_dependencies
from harp.core.asgi.messages import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.core.views.json import json
from harp.typing.global_settings import GlobalSettings


class SystemController(RoutingController):
    prefix = "/api/system"

    def __init__(self, *, settings: GlobalSettings, handle_errors=True, router=None):
        # a bit of scrambling for passwords etc.
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])

        self.settings = deepcopy(dict(settings))
        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    def configure(self):
        self.router.route(self.prefix + "/")(self.get)
        self.router.route(self.prefix + "/settings")(self.get_settings)
        self.router.route(self.prefix + "/dependencies")(self.get_dependencies)

    async def get(self, request: ASGIRequest, response: ASGIResponse):
        context = getattr(request, "context", {})

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    async def get_settings(self, request: ASGIRequest, response: ASGIResponse):
        return json(self.settings)

    async def get_dependencies(self, request: ASGIRequest, response: ASGIResponse):
        return json({"python": await self.__get_cached_python_dependencies()})

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies
