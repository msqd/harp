from typing import Type

from rodi import CannotResolveParameterException, Container
from whistle import IAsyncEventDispatcher

from harp.config import Config
from harp.core.asgi import ASGIKernel
from harp.core.asgi.events import EVENT_CORE_REQUEST, EVENT_CORE_VIEW
from harp.core.asgi.events.request import RequestEvent
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.event_dispatcher import LoggingAsyncEventDispatcher
from harp.core.views.json import on_json_response
from harp.errors import ProxyConfigurationError
from harp.protocols import ISettings
from harp.utils.network import Bind

from .events import EVENT_FACTORY_BIND, EVENT_FACTORY_BOUND, FactoryBindEvent, FactoryBoundEvent


async def ok_controller(request: ASGIRequest, response: ASGIResponse):
    await response.start(status=200)
    await response.body("Ok.")


async def on_health_request(event: RequestEvent):
    if event.request.path == "/healthz":
        event.set_controller(ok_controller)
        event.stop_propagation()


class KernelFactory:
    AsyncEventDispatcherType: Type[IAsyncEventDispatcher] = LoggingAsyncEventDispatcher
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(self, configuration: Config):
        self.configuration = configuration
        self.hostname = "[::]"

    async def build(self):
        # we only work on validated configuration
        self.configuration.validate()

        container = Container()
        dispatcher = self.build_event_dispatcher(container)
        resolver = ProxyControllerResolver()

        container.add_instance(self.configuration.settings, ISettings)

        self.configuration.register_events(dispatcher)
        await dispatcher.adispatch(
            EVENT_FACTORY_BIND,
            FactoryBindEvent(
                container,
                self.configuration.settings,
            ),
        )

        try:
            provider = container.build_provider()
        except CannotResolveParameterException as exc:
            raise ProxyConfigurationError("Cannot build container: unresolvable parameter.") from exc

        await dispatcher.adispatch(
            EVENT_FACTORY_BOUND,
            FactoryBoundEvent(
                provider,
                resolver,
                self.configuration.settings,
            ),
        )

        # self._on_create_configure_dashboard_if_needed(provider)
        # self._on_create_configure_endpoints(provider)

        return self.KernelType(dispatcher=dispatcher, resolver=resolver), [
            Bind(host=self.hostname, port=port) for port in resolver.ports
        ]

    def build_event_dispatcher(self, container):
        dispatcher = self.AsyncEventDispatcherType()
        dispatcher.add_listener(EVENT_CORE_REQUEST, on_health_request, priority=-100)

        # todo move into core or extension, this is not proxy related
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)
        container.add_instance(dispatcher, IAsyncEventDispatcher)
        return dispatcher
