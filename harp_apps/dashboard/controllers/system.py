import re
from copy import deepcopy

from harp import __revision__, __version__
from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest
from harp.typing.global_settings import GlobalSettings
from harp.views.json import json

from ..utils.dependencies import get_python_dependencies, parse_dependencies


@RouterPrefix("/api/system")
class SystemController(RoutingController):
    def __init__(self, *, settings: GlobalSettings, handle_errors=True, router=None):
        # a bit of scrambling for passwords etc.
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])

        self.settings = deepcopy(dict(settings))
        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/")
    async def get(self, request: HttpRequest):
        context = getattr(request, "context", {})

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    @GetHandler("/settings")
    async def get_settings(self):
        return json(self.settings)

    @GetHandler("/dependencies")
    async def get_dependencies(self):
        return json({"python": await self.__get_cached_python_dependencies()})

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies
