from typing import TYPE_CHECKING, Awaitable, Callable

from rodi import Container, Services
from whistle import Event

from harp.asgi import ASGIKernel
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

    def __init__(self, container: Container, settings):
        self.container = container
        self.settings = settings


EVENT_BIND = OnBindEvent.name

OnBindHandler = Callable[[OnBindEvent], Awaitable[None]]


class OnBoundEvent(Event):
    """
    «Bound» event happens after the service container is resolved, before the kernel creation.

    It is the right place to setup things that needs the container to be resolved (thus, you get a `provider` instead
    of a `container`).

    """

    name = "harp.config.bound"

    def __init__(self, provider: Services, resolver: "ProxyControllerResolver"):
        self.provider = provider
        self.resolver = resolver


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


EVENT_SHUTDOWN = OnShutdownEvent.name

OnShutdownHandler = Callable[[OnShutdownEvent], Awaitable[None]]
