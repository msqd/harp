from config.common import Configuration
from rodi import Container, Services
from whistle import Event

from harp.controllers import ProxyControllerResolver


class FactoryBindEvent(Event):
    """
    «Factory Bind» event happens before the service container is resolved.

    It is the right place to define services that may not be resolvable yet (because their dependencies may, or may not,
    be defined already).

    """

    name = "harp.config.bind"

    def __init__(self, container: Container, settings: Configuration):
        self.container = container
        self.settings = settings


EVENT_FACTORY_BIND = FactoryBindEvent.name


class FactoryBoundEvent(Event):
    """
    «Factory Bound» event happens after the service container is resolved, before the kernel creation.

    It is the right place to setup things that needs the container to be resolved (thus, you get a `provider` instead
    of a `container`).

    """

    name = "harp.config.bound"

    def __init__(self, provider: Services, resolver: ProxyControllerResolver):
        self.provider = provider
        self.resolver = resolver


EVENT_FACTORY_BOUND = FactoryBoundEvent.name


class FactoryBuildEvent(Event):
    """
    «Factory Build» event happens after the asgi kernel is created.

    It is the right place to decorate the kernel with middlewares.
    """

    name = "harp.config.build"

    def __init__(self, kernel, binds):
        self.kernel = kernel
        self.binds = binds


EVENT_FACTORY_BUILD = FactoryBuildEvent.name
