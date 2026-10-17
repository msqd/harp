import socket

from harp import get_logger
from harp.config.builders.system import System

logger = get_logger(__name__)


class UvicornAdapter:
    def __init__(self, system: System):
        self.system = system

    def _create_sockets(self):
        sockets = []
        for bind in self.system.binds:
            sock = socket.socket(socket.AF_INET6 if ":" in bind.host else socket.AF_INET)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind.host, bind.port))
            sock.set_inheritable(True)
            sockets.append(sock)
        return sockets

    async def serve(self):
        """
        Serves the proxy using uvicorn, on the running event loop (uvloop is chosen by the caller).
        """
        from uvicorn import Config, Server

        # logging is configured by harp (loggers "uvicorn.error" and "uvicorn.access"), loop is already running.
        config = Config(self.system.asgi_app, log_config=None, lifespan="on", loop="none")
        server = Server(config)
        logger.debug(f"🌎 {type(self).__name__}::serve({', '.join(map(str, self.system.binds))})")

        await server.serve(sockets=self._create_sockets())
        if not server.started:
            logger.error("Server initialization failed.")
            raise SystemExit(-1)
