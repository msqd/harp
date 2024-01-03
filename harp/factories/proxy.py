"""
:class:`ProxyFactory` is a helper to create proxies. It will load configuration, build services, create an
:class:`ASGIKernel <harp.core.asgi.kernel.ASGIKernel>` and prepare it for its future purpose.
"""
import dataclasses
from argparse import ArgumentParser
from collections import defaultdict
from functools import cached_property
from typing import Set, Type

from hypercorn.typing import ASGIFramework
from rodi import CannotResolveParameterException, CannotResolveTypeException, Container, Services
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.applications.dashboard.controllers import DashboardController
from harp.applications.dashboard.settings import DashboardSettings
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.events import EVENT_CORE_REQUEST, EVENT_CORE_VIEW
from harp.core.asgi.events.request import RequestEvent
from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.event_dispatcher import LoggingAsyncEventDispatcher
from harp.core.views.json import on_json_response
from harp.errors import ProxyConfigurationError
from harp.factories.events import EVENT_FACTORY_BIND
from harp.factories.events.bind import ProxyFactoryBindEvent
from harp.factories.settings import create_settings
from harp.protocols.storage import IStorage

_PROXY_ENDPOINT_OPTIONAL_KEYS = {"description"}
_PROXY_ENDPOINT_REQUIRED_KEYS = {"url", "name"}

logger = get_logger(__name__)


@dataclasses.dataclass(frozen=True)
class Bind:
    host: str
    port: int

    def __str__(self):
        return f"{self.host}:{self.port}"


class ProxyFactory:
    DEFAULT_DASHBOARD_PORT = 4080
    KernelType: Type[ASGIKernel] = ASGIKernel

    _binds: Set[Bind] = None

    @cached_property
    def binds(self) -> Set[Bind]:
        return self._binds

    def __init__(self, *, hostnames=("[::]",), settings=None, args=None):
        _options = self._get_values_from_arguments(args)
        self.settings = create_settings(
            settings, values=_options.values if _options else None, files=_options.files if _options else None
        )
        self.container = Container()
        self.dispatcher = self._create_event_dispatcher()

        self.resolver = ProxyControllerResolver()

        self._hostnames = hostnames
        self.__server_binds = set()

        self._binds = set()

        for extension in self.settings.values.get("extensions", []):
            self.load(extension)

        self.configure()

    def configure(self):
        pass

    def add(self, port, target, *, name=None, description=None):
        """
        Adds a port to proxy to a remote target (url).

        :param port: The port to listen on.
        :param target: The target url to proxy to.
        :param name: The name of the proxy. This is used to identify the proxy in the dashboard.
        :param description: The description of the proxy. Humans will like it like it (if we implement it...).
        """
        controller = HttpProxyController(target, name=name, dispatcher=self.dispatcher)
        self.resolver.add(port, controller)

        logger.info(f"🏭 :{port} -> {controller}")
        for hostname in self._hostnames:
            self.binds.add(Bind(hostname, port))

    def load(self, plugin):
        """
        Loads a python package that can register itself. The plugin spec will be thought about in the far future, but
        for now it mostly consists of a register function that takes a dispatcher as argument.

        :param plugin: The qualified path of the plugin to load.
        """
        try:
            plugin = __import__(plugin, fromlist=["register"])
        except ImportError as exc:
            raise RuntimeError(f"Module {plugin} does not have a register function or could not be imported.") from exc
        plugin.register(self.container, self.dispatcher, self.settings)

    async def create(self) -> ASGIFramework:
        """
        Builds the actual proxy as an ASGI application.

        :param args:
        :param kwargs:
        :return: ASGI application
        """

        # bind services

        await self.dispatcher.adispatch(EVENT_FACTORY_BIND, ProxyFactoryBindEvent(self.container, self.settings))

        try:
            provider = self.container.build_provider()
        except CannotResolveParameterException as exc:
            raise ProxyConfigurationError("Cannot build container: unresolvable parameter.") from exc
        self._on_create_configure_dashboard_if_needed(provider)
        self._on_create_configure_endpoints(provider)

        # noinspection PyTypeChecker
        return self.KernelType(dispatcher=self.dispatcher, resolver=self.resolver)

    def _get_values_from_arguments(self, args=None):
        """
        Parses sys.argv-like arguments.

        :param args:
        :return: argparse.Namespace

        """
        if not args:
            return None
        parser = ArgumentParser()
        parser.add_argument(
            "--set",
            "-s",
            action="append",
            dest="values",
            nargs=2,
            metavar=("KEY", "VALUE"),
            help="Set a configuration value.",
        )
        parser.add_argument("--file", "-f", action="append", dest="files", help="Load configuration from file.")
        return parser.parse_args(args)

    def _create_event_dispatcher(self):
        """Creates an event dispatcher and registers the default listeners."""
        dispatcher = LoggingAsyncEventDispatcher()

        async def ok_controller(request: ASGIRequest, response: ASGIResponse):
            await response.start(status=200)
            await response.body("Ok.")

        async def on_health_request(event: RequestEvent):
            if event.request.path == "/healthz":
                event.set_controller(ok_controller)
                event.stop_propagation()

        dispatcher.add_listener(EVENT_CORE_REQUEST, on_health_request, priority=-100)

        # todo move into core or extension, this is not proxy related
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)

        self.container.add_instance(dispatcher, IAsyncEventDispatcher)

        return dispatcher

    def _on_create_configure_endpoints(self, provider: Services):
        # should be refactored, read env for auto conf
        _ports = defaultdict(dict)

        try:
            _endpoints = self.settings.proxy.endpoints.values
        except AttributeError:
            _endpoints = {}

        for _port, _port_config in _endpoints.items():
            try:
                _port = int(_port)
            except TypeError as exc:
                raise ProxyConfigurationError(f"Invalid endpoint port {_port}.") from exc

            # check keys contains a required url, a required name, and an optional description
            if (
                _port_config.keys() != _PROXY_ENDPOINT_REQUIRED_KEYS
                and _port_config.keys() != _PROXY_ENDPOINT_OPTIONAL_KEYS | _PROXY_ENDPOINT_REQUIRED_KEYS
            ):
                raise ProxyConfigurationError(
                    f"Invalid endpoint configuration for port {_port} (required keys: "
                    f"{', '.join(_PROXY_ENDPOINT_REQUIRED_KEYS)}; optional keys: "
                    f"{', '.join(_PROXY_ENDPOINT_OPTIONAL_KEYS)}; got: {', '.join(_port_config.keys())})."
                )

            _ports[_port]["url"] = _port_config["url"]
            _ports[_port]["name"] = _port_config["name"]

        for _port, _port_config in _ports.items():
            self.add(_port, _port_config["url"], name=_port_config["name"], description=_port_config.get("description"))

    def _on_create_configure_dashboard_if_needed(self, provider: Services):
        self.settings._data.setdefault("dashboard", {})

        # for k, v in asdict(DashboardSettings()).items():
        #    self.settings._data["dashboard"].setdefault(k, v)
        dashboard_settings = self.settings.bind(DashboardSettings, "dashboard")
        self.settings._data["dashboard"] = dashboard_settings
        if not dashboard_settings.enabled:
            return

        try:
            storage = provider.get(IStorage)
            controller = DashboardController(storage=storage, settings=self.settings)
            self.resolver.add(dashboard_settings.port, controller)
            logger.info(f"🏭 :{dashboard_settings.port} -> {controller}")
            for hostname in self._hostnames:
                self.binds.add(Bind(hostname, dashboard_settings.port))

        except CannotResolveTypeException:
            logger.error(
                "Dashboard is enabled but no storage is configured. Dashboard will not be available. Did you forget "
                "to load a storage plugin?"
            )
