from typing import TYPE_CHECKING, Callable, Type, cast

from whistle import IAsyncEventDispatcher

from harp import __revision__, __version__, get_logger
from harp.asgi import ASGIKernel
from harp.asgi.events import EVENT_CORE_REQUEST, EVENT_CORE_VIEW
from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.services import Container, Services
from harp.typing import GlobalSettings
from harp.utils.network import Bind
from harp.views.json import on_json_response

from .. import ApplicationsRegistry
from ..events import (
    EVENT_BIND,
    EVENT_BOUND,
    EVENT_READY,
    EVENT_SHUTDOWN,
    OnBindEvent,
    OnBoundEvent,
    OnReadyEvent,
    OnShutdownEvent,
)

if TYPE_CHECKING:
    from harp.controllers import ProxyControllerResolver

logger = get_logger(__name__)


class System:
    """
    The core, global-like system objects, encapsulated together. Useful to manipulate the system from a high-level
    perspective, either from a server adapter point of view or from tests.

    Bootstrapping will create a System instance, which will be used to start the various subsystems. Then, the
    subsystems will work on their own, and should not need to have a system view.

    Attributes:
        config (GlobalSettings): The global configuration settings for the application.
        dispatcher (IAsyncEventDispatcher): The event dispatcher for handling application-wide events.
        provider (Services): The service provider for dependency injection and service management.
        kernel (ASGIKernel): The ASGI kernel for handling HTTP requests.
        binds (list[Bind]): A list of network binds specifying where the application should listen for incoming requests.

    Methods:
        dispose(): Asynchronously disposes of the system resources, primarily the ASGI kernel.
    """

    def __init__(
        self,
        config: GlobalSettings,
        dispatcher: IAsyncEventDispatcher,
        provider: Services,
        /,
        *,
        kernel: ASGIKernel,
        binds: list[Bind],
    ):
        self._config = config
        self._dispatcher = dispatcher
        self._provider = provider
        self._kernel = kernel
        self._binds = binds

    @property
    def config(self) -> GlobalSettings:
        return self._config

    @property
    def dispatcher(self) -> IAsyncEventDispatcher:
        return self._dispatcher

    @property
    def provider(self) -> Services:
        return self._provider

    @property
    def kernel(self) -> ASGIKernel:
        return self._kernel

    @property
    def binds(self) -> list[Bind]:
        return self._binds

    async def dispose(self):
        """
        Asynchronously disposes of the system resources, primarily the ASGI kernel.
        """
        if self.kernel:
            try:
                event = OnShutdownEvent(self.kernel, self.provider)
                await self.dispatcher.adispatch(EVENT_SHUTDOWN, event)
            except Exception as exc:
                logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_SHUTDOWN, exc)
                raise
            finally:
                self._kernel = None


class SystemBuilder:
    """
    A builder class for constructing the System instance, which represents the core of the HARP application.

    This class is responsible for assembling the necessary components of the System, including the global configuration,
    event dispatcher, service provider, and ASGI kernel, based on the provided configuration.

    Attributes:
        AsyncEventDispatcherType (Type[IAsyncEventDispatcher]): The type of the event dispatcher to use.
        ContainerType (Type[Container]): The type of the container to use for dependency injection.
        KernelType (Type[ASGIKernel]): The type of the ASGI kernel to use for handling HTTP requests.
        configuration_builder (ConfigurationBuilder): The configuration builder used to assemble the global configuration.
        hostname (str): The hostname where the application should listen for incoming requests.

    Methods:
        abuild() -> System: Asynchronously builds and returns an instance of the System class.
    """

    AsyncEventDispatcherType: Type[IAsyncEventDispatcher] = LoggingAsyncEventDispatcher
    ContainerType: Type[Container] = Container
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(
        self,
        applications=ApplicationsRegistry | Callable[[], ApplicationsRegistry],
        configuration=GlobalSettings | Callable[[], GlobalSettings],
        /,
        *,
        hostname: str = "[::]",
    ):
        self._applications = applications
        self._configuration = configuration
        self.hostname = hostname

    @property
    def applications(self) -> ApplicationsRegistry:
        if callable(self._applications):
            self._applications = self._applications()
        return self._applications

    @property
    def configuration(self) -> GlobalSettings:
        if callable(self._configuration):
            self._configuration = self._configuration()
        return self._configuration

    async def abuild(self) -> System:
        """
        Asynchronously builds and returns an instance of the System class, ready for use.

        Returns:
            System: An instance of the System class, assembled based on the provided configuration and components.
        """
        logger.info(f"🎙  HARP v.{__version__} ({__revision__})")

        # Get lazy configuration.
        config = self.configuration

        # Prepare and dispatch «bind» event.
        dispatcher = self.build_dispatcher()
        container = self.build_container(config, dispatcher)
        await self.dispatch_bind_event(dispatcher, container, config)

        # todo: this looks like not the right place, should not be tightly coupled to the factory
        from harp.controllers import ProxyControllerResolver

        controller_resolver = ProxyControllerResolver()
        container.add_instance(controller_resolver, ProxyControllerResolver)

        # Prepare and dispatch «bound» event.
        provider = container.build_provider()
        await self.dispatch_bound_event(dispatcher, provider, controller_resolver)

        # Build the kernel and dispatch «ready» event.
        event = await self.dispatch_ready_event(dispatcher, provider, controller_resolver)

        # Send back a coherent view of the system.
        return System(config, dispatcher, provider, kernel=event.kernel, binds=event.binds)

    def build_dispatcher(self):
        dispatcher = cast(IAsyncEventDispatcher, self.AsyncEventDispatcherType())
        self.applications.register_events(dispatcher)

        self.__setup_core_events(dispatcher)

        return dispatcher

    def __setup_core_events(self, dispatcher):
        # todo move into core or extension, this is not system or proxy related
        from harp.controllers.default import on_health_request

        dispatcher.add_listener(EVENT_CORE_REQUEST, on_health_request, priority=-100)
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)

    def build_container(self, config, dispatcher):
        container = cast(Container, self.ContainerType())
        container.add_instance(dispatcher, IAsyncEventDispatcher)
        container.add_instance(config, GlobalSettings)
        self.applications.register_services(container, config)
        return container

    async def dispatch_bind_event(
        self,
        dispatcher: IAsyncEventDispatcher,
        container: Container,
        config,
    ) -> OnBindEvent:
        # dispatch "bind" event: this is the last chance to add services to the container
        try:
            return cast(
                OnBindEvent,
                await dispatcher.adispatch(EVENT_BIND, OnBindEvent(container, config)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_BIND, exc)
            raise

    async def dispatch_bound_event(
        self,
        dispatcher: IAsyncEventDispatcher,
        provider: Services,
        resolver: "ProxyControllerResolver",
    ) -> OnBoundEvent:
        # dispatch "bound" event: you get a resolved container, do your thing
        try:
            return cast(
                OnBoundEvent,
                await dispatcher.adispatch(EVENT_BOUND, OnBoundEvent(provider, resolver)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_BOUND, exc)
            raise

    async def dispatch_ready_event(
        self,
        dispatcher: IAsyncEventDispatcher,
        provider: Services,
        controller_resolver: "ProxyControllerResolver",
    ):
        # todo: this should be instanciated by the service container, probably using a factory to dispatch the event,
        #  etc. Binds should not sit here, but where?
        kernel = self.KernelType(dispatcher=dispatcher, resolver=controller_resolver)
        binds = [Bind(host=self.hostname, port=port) for port in controller_resolver.ports]
        try:
            return cast(
                OnReadyEvent,
                await dispatcher.adispatch(EVENT_READY, OnReadyEvent(provider, kernel, binds)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_READY, exc)
            raise
