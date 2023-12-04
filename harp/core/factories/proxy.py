import logging

from hypercorn.typing import ASGIFramework

from harp.applications.proxy.controllers.http_proxy import HttpProxyController
from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.factories.container import create_container
from harp.core.factories.settings import create_settings
from harp.core.types.signs import Default


class ProxyFactory:
    def __init__(self, *, bind="localhost", settings=None, dashboard=True, dashboard_port=Default):
        self.config = create_settings(settings)
        self.container = create_container(self.config)
        self.resolver = ProxyControllerResolver()
        self.bind = bind
        self.binds = set()

        self.dashboard = dashboard
        self.dashboard_port = dashboard_port
        if self.dashboard_port is Default:
            self.dashboard_port = 4080

        if dashboard:
            # todo: use self.config['dashboard_enabled'] ???
            _port = self.config["dashboard_port"] if "dashboard_port" in self.config else dashboard_port
            self.configure_dashboard(port=_port)

    def configure_dashboard(self, *, port):
        port = 4080 if port is Default else port
        self.resolver.add(port, HttpProxyController(f"http://{self.bind}:4999/", name="ui"))
        self.binds.add(f"{self.bind}:{port}")

    def add(self, port, target, *, name=None):
        self.resolver.add(port, HttpProxyController(target, name=name))
        self.binds.add(f"{self.bind}:{port}")

    def create(self, *args, **kwargs) -> ASGIFramework:
        return ASGIKernel(*args, resolver=self.resolver, **kwargs)

    def create_hypercorn_config(self):
        from hypercorn.config import Config

        config = Config()
        config.bind = [*self.binds]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")
        return config

    def serve(self):
        import asyncio

        from hypercorn.asyncio import serve

        kernel = self.create()
        config = self.create_hypercorn_config()

        return asyncio.run(serve(kernel, config))


if __name__ == "__main__":
    proxy = ProxyFactory(dashboard_port=4040)
    proxy.add(8000, "https://httpbin.org/")
    proxy.serve()
