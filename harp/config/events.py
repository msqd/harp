from typing import TYPE_CHECKING, Awaitable, Callable

from whistle import Event

from harp.asgi import ASGIKernel
from harp.services import Container, Services
from harp.typing import GlobalSettings
from harp.utils.network import Bind

if TYPE_CHECKING:
    from harp.controllers import ProxyControllerResolver


class OnBindEvent(Event):
    """
    «Bind» event happens before the service container is resolved.

    It is the right place to define services that may not be resolvable yet (because their dependencies may, or may not,
    be defined already).

    """

    name = "harp.config.bind"

    #: Service container.
    container: Container

    #: Global settings.
    settings: GlobalSettings

    def __init__(self, container: Container, settings: GlobalSettings):
        self.container = container
        self.settings = settings


#: Event fired when the service container is being configured, before the dependencies are resolved. You can configure
#: any services in a listener to this event, but all dependencies must be resolvable once the event is fully dispatched.
EVENT_BIND = OnBindEvent.name

OnBindHandler = Callable[[OnBindEvent], Awaitable[None]]


class OnBoundEvent(Event):
    """
    «Bound» event happens after the service container is resolved, before the kernel creation.

    It is the right place to setup things that needs the container to be resolved (thus, you get a `provider` instead
    of a `container`).

    """

    name = "harp.config.bound"

    #: Services provider.
    provider: Services

    #: Proxy controller resolver.
    resolver: "ProxyControllerResolver"

    def __init__(self, provider: Services, resolver: "ProxyControllerResolver"):
        self.provider = provider
        self.resolver = resolver


#: Event fired when the service container is fully resolved, before the kernel is created. You can setup things that
#: require live instance of services here.
EVENT_BOUND = OnBoundEvent.name

OnBoundHandler = Callable[[OnBoundEvent], Awaitable[None]]


class OnReadyEvent(Event):
    """
    «Ready» event happens after the asgi kernel is created, just before the application starts.

    It is the right place to decorate the kernel with middlewares.

    """

    name = "harp.config.ready"

    def __init__(self, provider: Services, kernel: ASGIKernel, binds: list[Bind]):
        self.provider = provider
        self.kernel = kernel
        self.binds = binds


#: Event fired when the application is ready to start. You can decorate the kernel with middlewares here.
EVENT_READY = OnReadyEvent.name

OnReadyHandler = Callable[[OnReadyEvent], Awaitable[None]]


class OnShutdownEvent(Event):
    """
    «Shutdown» event happens when the application is stopping.

    """

    name = "harp.config.shutdown"

    def __init__(self, kernel: ASGIKernel, provider: Services):
        self.kernel = kernel
        self.provider = provider


#: Event fired when the application is shutting down. You can cleanup resources here.
EVENT_SHUTDOWN = OnShutdownEvent.name

OnShutdownHandler = Callable[[OnShutdownEvent], Awaitable[None]]
