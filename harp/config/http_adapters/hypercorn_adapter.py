import logging

from harp import get_logger

logger = get_logger(__name__)


class HypercornServerAdapter:
    def __init__(self, factory):
        self.factory = factory

    def _create_config(self, binds):
        """
        Creates a hypercorn config object.

        :return: hypercorn config object
        """
        from hypercorn.config import Config

        config = Config()
        config.bind = [*map(str, binds)]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")
        return config

    async def serve(self):
        """
        Creates and serves the proxy using hypercorn.
        """
        from hypercorn.asyncio import serve

        asgi_app, binds = await self.factory.build()
        config = self._create_config(binds)
        logger.info(f"🌎 HypercornServerAdapter.serve {config.bind}")
        return await serve(asgi_app, config)
