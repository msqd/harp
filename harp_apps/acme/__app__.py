from harp import get_logger
from harp.config import Application, OnBindEvent, OnBoundEvent, OnReadyEvent, OnShutdownEvent
from harp_apps.acme.settings import AcmeSettings

logger = get_logger(__name__)


async def on_bind(event: OnBindEvent):
    logger.warning("🔗 Binding Acme services")


async def on_bound(event: OnBoundEvent):
    logger.warning("🔗 Bound Acme services")


async def on_ready(event: OnReadyEvent):
    logger.warning("🔗 Building Acme services")


async def on_shutdown(event: OnShutdownEvent):
    logger.warning("🔗 Disposing Acme services")


application = Application(
    on_bind=on_bind,
    on_bound=on_bound,
    on_ready=on_ready,
    on_shutdown=on_shutdown,
    settings_type=AcmeSettings,
)
