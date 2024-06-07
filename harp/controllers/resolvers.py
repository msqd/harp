from typing import TYPE_CHECKING

from harp import get_logger

from .default import not_found_controller
from .typing import ControllerResolver

if TYPE_CHECKING:
    from harp.http import HttpRequest

logger = get_logger(__name__)


class DefaultControllerResolver(ControllerResolver):
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request: "HttpRequest"):
        return self.default_controller


class ProxyControllerResolver(DefaultControllerResolver):
    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._ports = {}

    @property
    def ports(self):
        return tuple(self._ports.keys())

    def add(self, port: int | str, controller):
        port = int(port)
        self._ports[port] = controller
        logger.info(f"🏭 Map: *:{port} -> {controller}")

    async def resolve(self, request: "HttpRequest"):
        return self._ports.get(request.server_port, self.default_controller)
