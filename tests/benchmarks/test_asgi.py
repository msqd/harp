import socket
import subprocess
import threading
import time

import httpx
import pytest

from harp.utils.network import get_available_network_port


def wait_for_port(port: int, host: str = "localhost", timeout: float = 5.0):
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
                    "Waited too long for the port {} on host {} to start accepting " "connections.".format(port, host)
                ) from ex


@pytest.fixture()
def service():
    port = get_available_network_port()

    class ServerThread(threading.Thread):
        daemon = True

        def run(self):
            self.process = subprocess.Popen(
                [
                    "harp",
                    "start",
                    "proxy",
                    "--set",
                    f"proxy.endpoints.{port}.url=http://localhost:8080/",
                    "--set",
                    f"proxy.endpoints.{port}.name=test",
                    "--set",
                    "dashboard.enabled=false",
                ],
                shell=False,
            )

    thread = ServerThread()
    thread.start()
    wait_for_port(port)

    yield port

    thread.join()


class TestAsgiProxyBenchmark:
    @pytest.mark.benchmark
    def test_foo(self, service, benchmark):
        @benchmark
        def result():
            return httpx.get(f"http://localhost:{service}/get")
