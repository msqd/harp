from typing import Optional, TypedDict

from harp import get_logger
from harp.config.asdict import mask_credentials
from harp.http import HttpRequest
from harp_apps.proxy.settings.endpoint import Endpoint

from .default import not_found_controller
from .typing import IAsyncController, IControllerResolver

logger = get_logger(__name__)


def _log_add_controller(controller, name, port):
    info = ["🏭"]
    if port is not None:
        info.append(f"*:{port} ->")
    info.append(mask_credentials(str(controller)))
    if name is not None:
        info.append(f"({name})")
    logger.info(" ".join(info))


class DefaultControllerResolver(IControllerResolver):
    def __init__(self, *, default_controller=None):
        self.default_controller = default_controller or not_found_controller

    async def resolve(self, request: HttpRequest):
        return self.default_controller


class _ControllerDefinitionForProxyControllerResolver(TypedDict):
    controller: IAsyncController
    name: Optional[str]
    port: Optional[int]
    host: Optional[str]


class ProxyControllerResolver(DefaultControllerResolver):
    _endpoints: dict[str, Endpoint]
    _controllers: list[_ControllerDefinitionForProxyControllerResolver]
    _port_to_controller_index: dict[int, int]
    _name_to_controller_index: dict[str, int]

    def __init__(self, *, default_controller=None):
        super().__init__(default_controller=default_controller)
        self._endpoints = {}
        self._controllers = []
        self._port_to_controller_index = {}
        self._name_to_controller_index = {}

    @property
    def endpoints(self) -> dict[str, Endpoint]:
        return self._endpoints

    @property
    def ports(self):
        return tuple(self._port_to_controller_index.keys())

    def host_for_port(self, port: int) -> Optional[str]:
        """Address a controller asked to be bound to, or None to use the server default."""
        return self._controllers[self._port_to_controller_index[port]]["host"]

    def __len__(self):
        return len(self._controllers)

    def __getitem__(self, index):
        return self._controllers[index]["controller"]

    def get_controller_port_by_index(self, index):
        return self._controllers[index]["port"]

    def get_controller_name_by_index(self, index):
        return self._controllers[index]["name"]

    def __setitem__(self, index, value):
        self._controllers[index]["controller"] = value

    def __iter__(self):
        yield from range(len(self))

    def add_endpoint(self, endpoint: Endpoint, *, controller: IAsyncController):
        if endpoint.settings.name in self._endpoints:
            raise RuntimeError(f"Endpoint «{endpoint.settings.name}» already exists.")
        self._endpoints[endpoint.settings.name] = endpoint

        self.add_controller(controller, name=endpoint.settings.name, port=endpoint.settings.port)

    def add_controller(
        self,
        controller: IAsyncController,
        *,
        name: Optional[str] = None,
        port: Optional[int],
        host: Optional[str] = None,
    ):
        if port is None and name is None:
            raise RuntimeError("Either port or name must be provided.")

        index = len(self)
        self._controllers.append({"controller": controller, "name": name, "port": port, "host": host})

        if port is not None:
            if port in self._port_to_controller_index:
                raise RuntimeError(f"Port «{port}» already in use.")
            self._port_to_controller_index[port] = index

        if name is not None:
            if name in self._name_to_controller_index:
                raise RuntimeError(f"Name «{name}» already in use.")
            self._name_to_controller_index[name] = index

        _log_add_controller(controller, name, port)

    async def resolve(self, request: HttpRequest):
        return self.resolve_by_port(request.server_port)

    def resolve_by_port(self, port: int):
        index = self._port_to_controller_index.get(port, None)

        if index is None or index >= len(self):
            return self.default_controller

        return self[index]

    def resolve_by_name(self, name: str):
        index = self._name_to_controller_index.get(name, None)

        if index is None or index >= len(self):
            return self.default_controller

        return self[index]
