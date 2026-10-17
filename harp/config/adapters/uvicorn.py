import asyncio
import contextlib
import signal
import socket

from harp import get_logger
from harp.config.builders.system import System

logger = get_logger(__name__)


def _create_server_type():
    from uvicorn import Server

    class _Server(Server):
        @contextlib.contextmanager
        def capture_signals(self):
            # uvicorn re-raises the signal it caught once stopped, which kills the process before the system is
            # disposed. Ask for a graceful exit instead and return normally.
            loop = asyncio.get_running_loop()
            signums = (signal.SIGINT, signal.SIGTERM)
            for signum in signums:
                loop.add_signal_handler(signum, self.handle_exit, signum, None)
            try:
                yield
            finally:
                for signum in signums:
                    loop.remove_signal_handler(signum)

    return _Server


class UvicornAdapter:
    def __init__(self, system: System):
        self.system = system

    def _create_sockets(self):
        sockets = []
        for bind in self.system.binds:
            host = bind.host.strip("[]")
            sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.family == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # dual stack, as hypercorn does
            sock.bind((host, bind.port))
            sock.set_inheritable(True)
            sockets.append(sock)
        return sockets

    async def serve(self):
        """
        Serves the proxy using uvicorn, on the running event loop (uvloop is chosen by the caller).
        """
        from uvicorn import Config

        # logging is configured by harp (loggers "uvicorn.error" and "uvicorn.access"), loop is already running.
        config = Config(
            self.system.asgi_app,
            log_config=None,
            lifespan="on",
            loop="none",
            interface="asgi3",  # "auto" takes a plain `__call__` (middlewares) for a double-callable ASGI 2 app
        )
        server = _create_server_type()(config)
        logger.debug(f"🌎 {type(self).__name__}::serve({', '.join(map(str, self.system.binds))})")

        await server.serve(sockets=self._create_sockets())
        if not server.started:
            logger.error("Server initialization failed.")
            raise SystemExit(-1)
