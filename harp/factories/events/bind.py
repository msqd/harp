from config.common import Configuration
from rodi import Container

from harp.core.event_dispatcher import BaseEvent


class ProxyFactoryBindEvent(BaseEvent):
    def __init__(self, container: Container, settings: Configuration):
        self.container = container
        self.settings = settings
