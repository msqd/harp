import asyncio
import dataclasses
import socket
import threading
import time
from contextlib import contextmanager
from typing import Awaitable, Callable, Optional

import httpx


def get_available_network_port():
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for_port(port: int, host: str = "localhost", timeout: float = 10.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port: Port number.
        host: Host address on which the port should exist.
        timeout: In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError(
                    "Waited too long for the port {} on host {} to start accepting connections.".format(port, host)
                ) from ex


class PortReservationManager:
    """Manages port reservations to prevent race conditions."""

    def __init__(self):
        self._reserved_ports = {}
        self._lock = threading.Lock()

    def reserve_port(self) -> int:
        """Reserve a port and keep the socket open until released."""
        with self._lock:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            self._reserved_ports[port] = sock
            return port

    def release_port(self, port: int):
        """Release a reserved port."""
        with self._lock:
            if port in self._reserved_ports:
                self._reserved_ports[port].close()
                del self._reserved_ports[port]

    @contextmanager
    def reserve_port_context(self):
        """Context manager for port reservation."""
        port = self.reserve_port()
        try:
            yield port
        finally:
            self.release_port(port)


# Global port manager instance
_port_manager = PortReservationManager()


def get_reserved_port() -> int:
    """Get an available port with reservation to prevent race conditions."""
    return _port_manager.reserve_port()


async def wait_for_service_ready(
    port: int,
    host: str = "localhost",
    health_path: Optional[str] = None,
    custom_check: Optional[Callable[[int], Awaitable[bool]]] = None,
    timeout: float = 10.0,
    retry_interval: float = 0.1,
):
    """Wait for a service to be ready by checking health endpoint or custom check.

    Args:
        port: Port number.
        host: Host address.
        health_path: Optional health check endpoint path.
        custom_check: Optional custom readiness check function.
        timeout: Total timeout in seconds.
        retry_interval: Time between retries in seconds.

    Raises:
        TimeoutError: If service is not ready within timeout.
    """
    start_time = time.perf_counter()
    base_url = f"http://{host}:{port}"

    while time.perf_counter() - start_time < timeout:
        try:
            if custom_check:
                if await custom_check(port):
                    return
            elif health_path:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{base_url}{health_path}")
                    if response.status_code == 200:
                        return
            else:
                # Fall back to simple port check
                with socket.create_connection((host, port), timeout=1):
                    return
        except Exception:
            await asyncio.sleep(retry_interval)

    raise TimeoutError(f"Service not ready on {host}:{port} after {timeout} seconds")


@dataclasses.dataclass(frozen=True)
class Bind:
    host: str
    port: int

    def __str__(self):
        return f"{self.host}:{self.port}"
