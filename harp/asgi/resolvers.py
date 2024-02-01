import json

from harp import get_logger
from harp.asgi.messages import ASGIRequest, ASGIResponse
from harp.utils.json import BytesEncoder

logger = get_logger(__name__)


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

    @property
    def ports(self):
        return tuple(self._ports.keys())

    def add(self, port: int | str, controller):
        port = int(port)
        self._ports[port] = controller
        logger.info(f"🏭 {type(self).__name__}::add(:{port} -> {controller})")

    async def resolve(self, request: ASGIRequest):
        return self._ports.get(request.port, self.default_controller)
