"""
:class:`ProxyFactory` is a helper to create proxies. It will load configuration, build services, create an
:class:`ASGIKernel <harp.core.asgi.kernel.ASGIKernel>` and prepare it for its future purpose.
"""

import logging
from typing import Type

from hypercorn.typing import ASGIFramework

from harp.applications.api.controllers import DashboardController
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.events import EVENT_CORE_REQUEST, EVENT_CORE_RESPONSE, EVENT_CORE_VIEW
from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.event_dispatcher import LoggingAsyncEventDispatcher
from harp.core.factories.container import create_container
from harp.core.factories.events.lifecycle import on_http_request, on_http_response
from harp.core.factories.settings import create_settings
from harp.core.types.signs import Default
from harp.core.views.json import on_json_response


class ProxyFactory:
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(self, *, bind="localhost", settings=None, dashboard=True, dashboard_port=Default):
        self.settings = create_settings(settings)
        self.container = create_container(self.settings)
        self.dispatcher = self.create_event_dispatcher()

        self.resolver = ProxyControllerResolver()
        self.bind = bind
        self.binds = set()

        self.dashboard = dashboard
        self.dashboard_port = dashboard_port
        if self.dashboard_port is Default:
            self.dashboard_port = 4080

        if dashboard:
            # todo: use self.config['dashboard_enabled'] ???
            _port = self.settings["dashboard_port"] if "dashboard_port" in self.settings else dashboard_port
            self.configure_dashboard(port=_port)

        print(self.settings.values)

    def create_event_dispatcher(self):
        """Creates an event dispatcher and registers the default listeners."""
        dispatcher = LoggingAsyncEventDispatcher()

        dispatcher.add_listener(EVENT_CORE_REQUEST, on_http_request, priority=-20)
        dispatcher.add_listener(EVENT_CORE_RESPONSE, on_http_response, priority=-20)
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)

        return dispatcher

    def configure_dashboard(self, *, port):
        port = 4080 if port is Default else port
        self.resolver.add(port, DashboardController())
        self.binds.add(f"{self.bind}:{port}")

    def add(self, port, target, *, name=None):
        """
        Adds a port to proxy to a remote target (url).

        :param port: The port to listen on.
        :param target: The target url to proxy to.
        :param name: The name of the proxy. This is used to identify the proxy in the dashboard.
        """
        self.resolver.add(port, HttpProxyController(target, name=name))
        self.binds.add(f"{self.bind}:{port}")

    def load(self, plugin):
        """
        Loads a python package that can register itself. The plugin spec will be thought about in the far future, but
        for now it mostly consists of a register function that takes a dispatcher as argument.

        :param plugin: The qualified path of the plugin to load.
        """
        try:
            plugin = __import__(plugin, fromlist=["register"])
        except ImportError as exc:
            raise RuntimeError(f"Module {plugin} does not have a register function.") from exc
        plugin.register(self.container, self.dispatcher, self.settings)

    def create(self, *args, **kwargs) -> ASGIFramework:
        """
        Builds the actual proxy as an ASGI application.

        :param args:
        :param kwargs:
        :return: ASGI application
        """
        # noinspection PyTypeChecker
        return self.KernelType(*args, dispatcher=self.dispatcher, resolver=self.resolver, **kwargs)

    def create_hypercorn_config(self):
        """
        Creates a hypercorn config object.

        :return: hypercorn config object
        """
        from hypercorn.config import Config

        config = Config()
        config.bind = [*self.binds]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")
        return config

    def serve(self):
        """
        Creates and serves the proxy using hypercorn.
        """
        import asyncio

        from hypercorn.asyncio import serve

        kernel = self.create()
        config = self.create_hypercorn_config()

        return asyncio.run(serve(kernel, config))


if __name__ == "__main__":
    proxy = ProxyFactory(dashboard_port=4040)
    proxy.add(8000, "https://httpbin.org/")
    proxy.load("harp.contrib.sqlalchemy_storage")
    proxy.serve()
