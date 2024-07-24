from harp import get_logger
from harp.config import Application

logger = get_logger(__name__)


class AcmeLifecycle(Application.Lifecycle):
    @staticmethod
    async def on_bind(event):
        logger.warning("🔗 Binding Acme services")

    @staticmethod
    async def on_bound(event):
        logger.warning("🔗 Bound Acme services")

    @staticmethod
    async def on_build(event):
        logger.warning("🔗 Building Acme services")

    @staticmethod
    async def on_dispose(event):
        logger.warning("🔗 Disposing Acme services")
