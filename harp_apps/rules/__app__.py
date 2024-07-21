from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.config import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent

from .settings import RulesSettings
from .subscribers import RulesSubscriber

logger = get_logger(__name__)


class RulesApplication(Application):
    settings_namespace = "rules"
    settings_type = RulesSettings
    subscriber = None

    async def on_bind(self, event: FactoryBindEvent):
        logger.warning("📦 Rules are currently experimental. THE API MAY CHANGE A LOT.")
        logger.warning("📦 Rules: found %d rules.", len(self.settings.rules))

    async def on_bound(self, event: FactoryBoundEvent):
        dispatcher = event.provider.get(IAsyncEventDispatcher)
        self.subscriber = RulesSubscriber(self.settings.rules)
        self.subscriber.subscribe(dispatcher)

    async def on_dispose(self, event: FactoryDisposeEvent):
        dispatcher = event.provider.get(IAsyncEventDispatcher)
        self.subscriber.unsubscribe(dispatcher)
        self.subscriber = None
