from typing import TYPE_CHECKING, Optional

from httpx import AsyncClient
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.models import Endpoint
from harp_apps.proxy.settings import EndpointSettings

from .default import not_found_controller
from .typing import ControllerResolver

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class DefaultControllerResolver(ControllerResolver):
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request: HttpRequest):
        return self.default_controller


class ProxyControllerResolver(DefaultControllerResolver):
    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._endpoints = {}
        self._ports = {}

    @property
    def endpoints(self):
        return self._endpoints

    @property
    def ports(self):
        return tuple(self._ports.keys())

    def add(
        self,
        endpoint_settings: EndpointSettings,
        *,
        http_client: AsyncClient,
        dispatcher: Optional[IAsyncEventDispatcher] = None,
    ):
        if endpoint_settings.name in self._endpoints:
            raise RuntimeError(f"Endpoint «{endpoint_settings.name}» already exists.")

        if endpoint_settings.port in self._ports:
            raise RuntimeError(f"Port «{endpoint_settings.port}» already in use.")

        self._endpoints[endpoint_settings.name] = endpoint = Endpoint(endpoint_settings)
        controller = HttpProxyController(
            endpoint.remote, dispatcher=dispatcher, http_client=http_client, name=endpoint_settings.name
        )
        self._ports[endpoint_settings.port] = controller
        logger.info(f"🏭 Map: *:{endpoint.port} -> {controller}")

    def add_controller(self, port: int, controller):
        if port in self._ports:
            raise RuntimeError(f"Port «{port}» already in use.")
        self._ports[port] = controller

    async def resolve(self, request: HttpRequest):
        return self._ports.get(request.server_port, self.default_controller)
