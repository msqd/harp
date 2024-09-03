import logging
import sys
from typing import cast

from asgi_tools.types import TASGIApp
from asyncpg import PostgresError

from harp import get_logger
from harp.config.builders.system import System
from harp.settings import USE_PROMETHEUS

logger = get_logger(__name__)


class HypercornAdapter:
    def __init__(self, system: System):
        self.system = system

    def _create_hypercorn_config(self, binds):
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
        from hypercorn.typing import Framework
        from hypercorn.utils import LifespanFailureError

        asgi_app = cast(TASGIApp, self.system.kernel)
        if USE_PROMETHEUS:
            from asgi_prometheus import PrometheusMiddleware

            _metrics_url = "/.prometheus/metrics"
            asgi_app = PrometheusMiddleware(asgi_app, metrics_url=_metrics_url, group_paths=["/"])
            asgi_app.scopes = ("http",)
            logger.info(f"🌎 PrometheusMiddleware enabled, metrics under {_metrics_url}.")

        hypercorn_config = self._create_hypercorn_config(self.system.binds)
        logger.debug(f"🌎 {type(self).__name__}::serve({', '.join(hypercorn_config.bind)})")

        try:
            return await serve(cast(Framework, asgi_app), hypercorn_config, mode="asgi")
        except LifespanFailureError as exc:
            logger.exception(
                f"Server initiliation failed: {repr(exc.__cause__)}",
                exc_info=exc.__cause__,
            )
            if isinstance(exc.__cause__, PostgresError):
                logger.error("Could not connect to underlying postgres storage backend, check your config.")

            sys.exit(-1)
