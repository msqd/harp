"""A real ``harp-proxy`` process, started and stopped by a probe."""

import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

from harp.utils.network import get_available_network_port, wait_for_port


def scrubbed_environment(home: Path) -> dict[str, str]:
    """What a process under probe inherits: no colour variable, nothing from the developer's shell."""
    return {"PATH": os.environ.get("PATH", ""), "HOME": str(home)}


def console_script(name: str) -> str:
    return str(Path(sys.executable).parent / name)


def backend_of(storage_url: str) -> str:
    return storage_url.split("://", 1)[0]


class ProxyServer:
    """``harp-proxy server`` on free ports, with endpoints and a dashboard, in a scrubbed environment."""

    def __init__(self, directory: Path, *, storage_url: str, endpoints: list[dict], dashboard: dict | None = None):
        self.directory = directory
        self.storage_url = storage_url
        self.dashboard_port = get_available_network_port()
        self.endpoint_ports = {endpoint["name"]: get_available_network_port() for endpoint in endpoints}
        self.config_path = directory / "harp.yml"
        self.log_path = directory / "harp.log"
        self.config_path.write_text(
            yaml.safe_dump(
                {
                    "applications": [
                        "harp_apps.proxy",
                        "harp_apps.storage",
                        "harp_apps.dashboard",
                        "harp_apps.http_client",
                    ],
                    "storage": {"url": storage_url},
                    "dashboard": {"port": self.dashboard_port, **(dashboard or {})},
                    "proxy": {
                        "endpoints": [
                            {**endpoint, "port": self.endpoint_ports[endpoint["name"]]} for endpoint in endpoints
                        ]
                    },
                }
            )
        )
        self._process: subprocess.Popen | None = None

    @property
    def backend(self) -> str:
        return backend_of(self.storage_url)

    def start(self) -> "ProxyServer":
        log = self.log_path.open("wb")
        self._process = subprocess.Popen(
            [console_script("harp-proxy"), "server", "--file", str(self.config_path)],
            cwd=self.directory,
            env=scrubbed_environment(self.directory),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for port in (*self.endpoint_ports.values(), self.dashboard_port):
                self._wait_for(port)
        except BaseException:
            self.stop()
            raise
        return self

    def _wait_for(self, port: int, timeout: float = 60.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f"harp-proxy exited with {self._process.returncode}:\n{self.log()}")
            try:
                wait_for_port(port, "127.0.0.1", 0.5)
                return
            except Exception:  # noqa: BLE001 - not listening yet
                continue
        raise RuntimeError(f"harp-proxy never listened on {port}:\n{self.log()}")

    def log(self) -> str:
        return self.log_path.read_text(errors="replace")

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(15)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
