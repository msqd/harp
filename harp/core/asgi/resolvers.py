import json

from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.utils.json import BytesEncoder


async def dump_request_controller(request: ASGIRequest, response: ASGIResponse):
    response.headers["content-type"] = "application/json"
    await response.start()
    await response.body(json.dumps(request.scope, cls=BytesEncoder))


async def not_found_controller(request: ASGIRequest, response: ASGIResponse):
    response.headers["content-type"] = "text/plain"
    await response.start(status=404)
    await response.body("Not found.")


class ControllerResolver:
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request: ASGIRequest):
        return self.default_controller


class ProxyControllerResolver(ControllerResolver):
    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._ports = {}

    def add(self, port: int | str, controller):
        self._ports[int(port)] = controller

    async def resolve(self, request: ASGIRequest):
        return self._ports.get(request.port, self.default_controller)
