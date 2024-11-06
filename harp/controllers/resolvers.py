from typing import TYPE_CHECKING

from harp import get_logger
from harp.http import HttpRequest
from harp_apps.proxy.settings.endpoint import Endpoint

from .default import not_found_controller
from .typing import IAsyncController, IControllerResolver

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class DefaultControllerResolver(IControllerResolver):
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request: HttpRequest):
        return self.default_controller


class ProxyControllerResolver(DefaultControllerResolver):
    _endpoints: dict[str, Endpoint]
    _ports: dict[int, IAsyncController]

    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._endpoints = {}
        self._ports = {}

    @property
    def endpoints(self) -> dict[str, Endpoint]:
        return self._endpoints

    @property
    def ports(self):
        return tuple(self._ports.keys())

    def add(
        self,
        endpoint: Endpoint,
        *,
        controller: IAsyncController,
    ):
        if endpoint.settings.name in self._endpoints:
            raise RuntimeError(f"Endpoint «{endpoint.settings.name}» already exists.")

        if endpoint.settings.port in self._ports:
            raise RuntimeError(f"Port «{endpoint.settings.port}» already in use.")

        self._endpoints[endpoint.settings.name] = endpoint
        self.add_controller(endpoint.settings.port, controller)

    def add_controller(self, port: int, controller: IAsyncController):
        if port in self._ports:
            raise RuntimeError(f"Port «{port}» already in use.")
        self._ports[port] = controller
        logger.info(f"🏭 Map: *:{port} -> {controller}")

    async def resolve(self, request: HttpRequest):
        return self._ports.get(request.server_port, self.default_controller)
