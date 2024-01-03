import logging

from harp import get_logger
from harp.factories.adapters.base import AbstractServerAdapter

logger = get_logger(__name__)


class HypercornServerAdapter(AbstractServerAdapter):
    def _create_config(self):
        """
        Creates a hypercorn config object.

        :return: hypercorn config object
        """
        from hypercorn.config import Config

        config = Config()
        config.bind = [*map(str, self.wrapped.binds)]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")
        return config

    async def serve(self):
        """
        Creates and serves the proxy using hypercorn.
        """
        from hypercorn.asyncio import serve

        app = await self.wrapped.create()
        config = self._create_config()
        logger.info(f"HypercornServerAdapter.serve {config.bind}")
        return await serve(app, config)
