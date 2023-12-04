import json

from harp.core.asgi.requests import ASGIRequest
from harp.core.asgi.responders import ASGIResponder
from harp.utils.json import BytesEncoder


async def dump_request_controller(request: ASGIRequest, response: ASGIResponder):
    await response.start(headers={"content-type": "application/json"})
    await response.body(json.dumps(request.scope, cls=BytesEncoder))


async def not_found_controller(request: ASGIRequest, response: ASGIResponder):
    await response.start(headers={"content-type": "text/plain"}, status=404)
    await response.body("Not found.")


class ControllerResolver:
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request):
        return self.default_controller


class ProxyControllerResolver(ControllerResolver):
    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._ports = {}

    def add(self, port, controller):
        self._ports[port] = controller

    async def resolve(self, request):
        return self._ports.get(request.port, self.default_controller)
