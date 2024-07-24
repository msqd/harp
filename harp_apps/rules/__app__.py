from harp import get_logger
from harp.config.applications import Application
from harp.config.events import FactoryBindEvent, FactoryBoundEvent, FactoryDisposeEvent

from .settings import RulesSettings
from .subscribers import RulesSubscriber

logger = get_logger(__name__)

RULES_SUBSCRIBER = "rules.subscriber"


class RulesLifecycle(Application.Lifecycle):
    @staticmethod
    async def on_bind(event: FactoryBindEvent):
        settings = event.settings.get("rules")
        logger.warning("📦 Rules are currently experimental. THE API MAY CHANGE A LOT.")
        logger.warning("📦 Rules: found %d rules.", len(settings.rules))

    @staticmethod
    async def on_bound(event: FactoryBoundEvent):
        settings = event.provider.get(RulesSettings)
        subscriber = RulesSubscriber(settings.rules)
        subscriber.subscribe(event.dispatcher)
        event.provider.set(RULES_SUBSCRIBER, subscriber)

    @staticmethod
    async def on_dispose(event: FactoryDisposeEvent):
        subscriber = event.provider.get(RULES_SUBSCRIBER)
        subscriber.unsubscribe(event.dispatcher)


class RulesApplication(Application):
    Settings = RulesSettings
    Lifecycle = RulesLifecycle
