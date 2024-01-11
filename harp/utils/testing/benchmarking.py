import os
import subprocess
import threading
from string import Template
from tempfile import NamedTemporaryFile

import httpx
import pytest

from harp import get_logger
from harp.utils.network import get_available_network_port, wait_for_port

logger = get_logger(__name__)


class RunHarpProxyInSubprocessThread(threading.Thread):
    daemon = True

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None, config=None):
        super().__init__(group, target, name, args, kwargs, daemon=daemon)

        self.config_filename = None
        if config:
            with NamedTemporaryFile("w+", suffix=".yaml", delete=False) as _tmpfile_config:
                _tmpfile_config.write(config or "")
                self.config_filename = _tmpfile_config.name

    def run(self):
        args = [
            "harp",
            "start",
            "server",
            *(("--file", self.config_filename) if self.config_filename else ()),
        ]
        logger.info('Starting subprocess: "%s"', " ".join(args))
        self.process = subprocess.Popen(args, shell=False)

    def join(self, timeout=None):
        if self.config_filename:
            os.unlink(self.config_filename)
        return super().join(timeout)


class AbstractProxyBenchmark:
    config = Template("")

    @pytest.fixture(scope="class")
    def proxy(self):
        port = get_available_network_port()
        thread = RunHarpProxyInSubprocessThread(config=self.config.substitute(port=port))
        try:
            try:
                from pytest_cov.embed import cleanup_on_sigterm
            except ImportError:
                pass
            else:
                cleanup_on_sigterm()
            thread.start()
            wait_for_port(port, timeout=10.0)
            yield f"localhost:{port}"
        finally:
            thread.join()

    def test_noproxy_get(self, benchmark):
        @benchmark
        def result():
            return httpx.get("http://localhost:8080/get")

    def test_httpbin_get(self, benchmark, proxy):
        @benchmark
        def result():
            return httpx.get(f"http://{proxy}/get")
