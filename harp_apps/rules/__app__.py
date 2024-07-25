from harp import get_logger
from harp.config.applications import Application
from harp.config.events import OnBindEvent, OnBoundEvent, OnShutdownEvent

from .settings import RulesSettings
from .subscribers import RulesSubscriber

logger = get_logger(__name__)

RULES_SUBSCRIBER = "rules.subscriber"


async def on_bind(event: OnBindEvent):
    settings = event.settings.get("rules")
    logger.warning("📦 Rules are currently experimental. THE API MAY CHANGE A LOT.")
    logger.warning("📦 Rules: found %d rules.", len(settings.ruleset))


async def on_bound(event: OnBoundEvent):
    settings = event.provider.get(RulesSettings)
    subscriber = RulesSubscriber(settings.ruleset)
    subscriber.subscribe(event.dispatcher)
    event.provider.set(RULES_SUBSCRIBER, subscriber)


async def on_shutdown(event: OnShutdownEvent):
    subscriber = event.provider.get(RULES_SUBSCRIBER)
    subscriber.unsubscribe(event.dispatcher)


application = Application(
    settings_type=RulesSettings,
    on_bind=on_bind,
    on_bound=on_bound,
    on_shutdown=on_shutdown,
)
