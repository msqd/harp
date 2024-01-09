from config.common import Configuration
from rodi import Container, Services
from whistle import Event

from harp.core.asgi.resolvers import ProxyControllerResolver

EVENT_FACTORY_BIND = "harp.config.bind"
EVENT_FACTORY_BOUND = "harp.config.bound"


class FactoryBindEvent(Event):
    def __init__(self, container: Container, settings: Configuration):
        self.container = container
        self.settings = settings


class FactoryBoundEvent(Event):
    def __init__(self, provider: Services, resolver: ProxyControllerResolver, settings: Configuration):
        self.provider = provider
        self.resolver = resolver
        self.settings = settings
