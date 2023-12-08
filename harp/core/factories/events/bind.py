from config.common import Configuration
from rodi import Container

from harp.core.asgi.events.base import BaseEvent


class ProxyFactoryBindEvent(BaseEvent):
    def __init__(self, container: Container, settings: Configuration):
        self.container = container
        self.settings = settings
