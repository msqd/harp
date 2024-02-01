import re
from copy import deepcopy

import networkx
from bokeh.embed import json_item
from bokeh.plotting import figure, from_networkx

from harp import __revision__, __version__
from harp.asgi import ASGIRequest, ASGIResponse
from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.typing.global_settings import GlobalSettings
from harp.views.json import json

from ..utils.dependencies import get_python_dependencies, parse_dependencies


@RouterPrefix("/api/system")
class SystemController(RoutingController):
    def __init__(self, *, settings: GlobalSettings, handle_errors=True, router=None):
        self.settings = settings = deepcopy(dict(settings))

        # a bit of scrambling for passwords etc.
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])

        self._dependencies = None

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/")
    async def get(self, request: ASGIRequest, response: ASGIResponse):
        context = getattr(request, "context", {})

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    @GetHandler("/settings")
    async def get_settings(self, request: ASGIRequest, response: ASGIResponse):
        return json(self.settings)

    @GetHandler("/dependencies")
    async def get_dependencies(self, request: ASGIRequest, response: ASGIResponse):
        return json({"python": await self.__get_cached_python_dependencies()})

    @GetHandler("/topology")
    async def get_topology(self, request: ASGIRequest, response: ASGIResponse):
        graph = networkx.DiGraph()
        graph.add_node(0, name="Harp")

        plot = figure(
            title="Topology",
            x_range=(-1.1, 1.1),
            y_range=(-1.1, 1.1),
            tools="",
            toolbar_location=None,
        )

        graph = from_networkx(graph, networkx.spring_layout, scale=2, center=(0, 0))
        plot.renderers.append(graph)
        return json(json_item(plot))

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies
