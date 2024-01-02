from config.common import Configuration
from rodi import Container
from whistle import Event


class ProxyFactoryBindEvent(Event):
    def __init__(self, container: Container, settings: Configuration):
        self.container = container
        self.settings = settings
