import asyncio
import signal

from harp import get_logger
from harp.config.builders.system import System

logger = get_logger(__name__)


class GranianAdapter:
    def __init__(self, system: System):
        self.system = system

    def _create_servers(self):
        from granian.constants import Interfaces
        from granian.server.embed import Server

        # The embedded server listens on one address only: the first bind carries the ASGI lifespan, the others serve
        # the same app without it (the lifespan must run once).
        return [
            Server(
                self.system.asgi_app,
                address=bind.host,
                port=bind.port,
                interface=Interfaces.ASGI if index == 0 else Interfaces.ASGINL,
                log_enabled=False,
            )
            for index, bind in enumerate(self.system.binds)
        ]

    async def serve(self):
        """
        Serves the proxy using granian's embedded (experimental) server, on the running event loop.
        """
        servers = self._create_servers()
        logger.debug(f"🌎 {type(self).__name__}::serve({', '.join(map(str, self.system.binds))})")

        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signum, lambda: [server.stop() for server in servers])

        try:
            await asyncio.gather(*(server.serve() for server in servers))
        finally:
            for server in servers:
                server.stop()
