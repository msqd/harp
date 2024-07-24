from typing import Type, cast

from rodi import Container, Services
from whistle import IAsyncEventDispatcher

from harp import __revision__, __version__, get_logger
from harp.asgi import ASGIKernel
from harp.controllers import ProxyControllerResolver
from harp.event_dispatcher import LoggingAsyncEventDispatcher
from harp.typing import GlobalSettings

from ...asgi.events import EVENT_CONTROLLER_VIEW, EVENT_CORE_REQUEST
from ...controllers.default import on_health_request
from ...utils.network import Bind
from ...views.json import on_json_response
from ..events import (
    EVENT_FACTORY_BIND,
    EVENT_FACTORY_BOUND,
    EVENT_FACTORY_BUILD,
    EVENT_FACTORY_DISPOSE,
    FactoryBindEvent,
    FactoryBoundEvent,
    FactoryBuildEvent,
    FactoryDisposeEvent,
)
from .configuration import ConfigurationBuilder

logger = get_logger(__name__)


class System:
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
        if self.kernel:
            event = FactoryDisposeEvent(self.kernel, self.provider)
            await self.dispatcher.adispatch(EVENT_FACTORY_DISPOSE, event)
            self._kernel = None


class SystemBuilder:
    AsyncEventDispatcherType: Type[IAsyncEventDispatcher] = LoggingAsyncEventDispatcher
    ContainerType: Type[Container] = Container
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(self, configuration_builder: ConfigurationBuilder, /, *, hostname: str = "[::]"):
        self.configuration_builder = configuration_builder
        self.hostname = hostname

    @property
    def applications(self):
        return self.configuration_builder.applications

    async def abuild(self) -> System:
        logger.info(f"🎙  HARP v.{__version__} ({__revision__})")

        # Get the config ready.
        config = self.configuration_builder.build()

        # Prepare and dispatch «bind» event.
        dispatcher = self.build_dispatcher()
        container = self.build_container(config, dispatcher)
        await self.dispatch_bind_event(dispatcher, container, config)

        # todo: this looks like not the right place, should not be tightly coupled to the factory
        controller_resolver = ProxyControllerResolver()
        container.add_instance(controller_resolver, ProxyControllerResolver)

        # Prepare and dispatch «bound» event.
        provider = container.build_provider()
        await self.dispatch_bound_event(dispatcher, provider, controller_resolver)

        # Build the kernel and dispatch «build» event.
        event = await self.dispatch_build_event(dispatcher, provider, controller_resolver)

        # Send back a coherent view of the system.
        return System(config, dispatcher, provider, kernel=event.kernel, binds=event.binds)

    def build_dispatcher(self):
        dispatcher = cast(IAsyncEventDispatcher, self.AsyncEventDispatcherType())
        self.applications.register_events(dispatcher)

        self.__setup_core_events(dispatcher)

        return dispatcher

    def __setup_core_events(self, dispatcher):
        # todo move into core or extension, this is not system or proxy related
        dispatcher.add_listener(EVENT_CORE_REQUEST, on_health_request, priority=-100)
        dispatcher.add_listener(EVENT_CONTROLLER_VIEW, on_json_response)

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
    ) -> FactoryBindEvent:
        # dispatch "bind" event: this is the last chance to add services to the container
        try:
            return cast(
                FactoryBindEvent,
                await dispatcher.adispatch(EVENT_FACTORY_BIND, FactoryBindEvent(container, config)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_FACTORY_BIND, exc)
            raise

    async def dispatch_bound_event(
        self,
        dispatcher: IAsyncEventDispatcher,
        provider: Services,
        resolver: ProxyControllerResolver,
    ) -> FactoryBoundEvent:
        # dispatch "bound" event: you get a resolved container, do your thing
        try:
            return cast(
                FactoryBoundEvent,
                await dispatcher.adispatch(EVENT_FACTORY_BOUND, FactoryBoundEvent(provider, resolver)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_FACTORY_BOUND, exc)
            raise

    async def dispatch_build_event(
        self,
        dispatcher: IAsyncEventDispatcher,
        provider: Services,
        controller_resolver: ProxyControllerResolver,
    ):
        # todo: this should be instanciated by the service container, probably using a factory to dispatch the event,
        #  etc. Binds should not sit here, but where?
        kernel = self.KernelType(dispatcher=dispatcher, resolver=controller_resolver)
        binds = [Bind(host=self.hostname, port=port) for port in controller_resolver.ports]
        try:
            return cast(
                FactoryBuildEvent,
                await dispatcher.adispatch(EVENT_FACTORY_BUILD, FactoryBuildEvent(provider, kernel, binds)),
            )
        except Exception as exc:
            logger.fatal("💣 Fatal while dispatching «%s» event: %s", EVENT_FACTORY_BUILD, exc)
            raise
