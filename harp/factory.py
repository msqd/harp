import logging
from collections import defaultdict
from copy import deepcopy
from types import MappingProxyType

import anyio

from harp.errors import ProxyError
from harp.models.proxy_endpoint import ProxyEndpoint
from harp.proxy import Proxy, auto
from harp.services import create_config, create_container
from harp.types import _default


class ProxyFactory:
    ProxyType = Proxy

    def __init__(self, *, settings=None, port=4000, ui=True, ui_port=_default, ProxyType=None):
        self.config = create_config(settings)
        self.container = create_container(self.config)

        self.ProxyType = ProxyType or self.ProxyType

        self.ports = {}
        self._next_available_port = port

        # should be refactored, read env for auto conf
        _ports = defaultdict(dict)
        for k, v in self.config.values.items():
            if k.startswith("proxy_endpoint_"):
                _port, _prop = k[15:].split("_")
                try:
                    _port = int(_port)
                except TypeError as exc:
                    raise ProxyError(f"Invalid endpoint port {_port}.") from exc
                if _prop not in ("name", "target"):
                    raise ProxyError(f"Invalid endpoint property {_prop}.")
                _ports[_port][_prop] = v

        for _port, _port_config in _ports.items():
            self.add(**_port_config, port=_port)

        if ui:
            # self.config['dashboard_enabled']
            if "dashboard_port" in self.config:
                ui_port = self.config["dashboard_port"]
            if ui_port is _default:
                ui_port = 4080
            endpoint = ProxyEndpoint("http://localhost:4999/", name="ui")
            self.ports[int(ui_port or self.next_available_port())] = endpoint

    def next_available_port(self):
        while self._next_available_port in self.ports:
            self._next_available_port += 1
        try:
            return self._next_available_port
        finally:
            self._next_available_port += 1

    def add(self, target, *, port=auto, name=None):
        if port is auto:
            port = self.next_available_port()

        self.ports[port] = ProxyEndpoint(target, name=name)
        return self.ports[port]

    def create(self, *args, **kwargs):
        """
        Builds the proxy instance with the current configuration.

        We try to use readonly containers as much as possible to avoid side effects of runtime configuration changes.
        But if you really want to, you'll find a way. Real question being why would you want to?

        :return: Proxy instance
        """
        return self.ProxyType(
            *args, endpoints=MappingProxyType(deepcopy(self.ports)), container=self.container, **kwargs
        )

    def run(self):
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        proxy = self.create()

        config = Config()
        config.bind = [f"0.0.0.0:{port}" for port in proxy._endpoints]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")

        anyio.run(serve, proxy, config, backend="asyncio", backend_options={"use_uvloop": True})
