import logging
import sys

from asyncpg import PostgresError
from hypercorn.utils import LifespanFailureError

from harp import get_logger
from harp.utils.env import get_bool_from_env

logger = get_logger(__name__)


class HypercornAdapter:
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
        config.workers = 8
        return config

    async def serve(self):
        """
        Creates and serves the proxy using hypercorn.
        """
        from hypercorn.asyncio import serve

        asgi_app, binds = await self.factory.build()

        if get_bool_from_env("USE_ASGI_PROMETHEUS_MIDDLEWARE", False):
            from asgi_prometheus import PrometheusMiddleware

            _metrics_url = "/.prometheus/metrics"
            asgi_app = PrometheusMiddleware(asgi_app, metrics_url=_metrics_url, group_paths=["/"])
            logger.info(f"🌎 PrometheusMiddleware enabled, metrics under {_metrics_url}.")

        config = self._create_config(binds)
        logger.debug(f"🌎 {type(self).__name__}::serve({', '.join(config.bind)})")

        try:
            return await serve(asgi_app, config, mode="asgi")
        except LifespanFailureError as exc:
            logger.exception(f"Server initiliation failed: {repr(exc.__cause__)}", exc_info=exc.__cause__)
            if isinstance(exc.__cause__, PostgresError):
                logger.error("Could not connect to underlying postgres storage backend, check your config.")

            sys.exit(-1)
