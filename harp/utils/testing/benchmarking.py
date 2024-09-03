import os
import shlex
import subprocess
import threading
from string import Template
from tempfile import NamedTemporaryFile

import httpx
import pytest

from harp import get_logger
from harp.commandline.start import assert_development_packages_are_available
from harp.utils.network import get_available_network_port, wait_for_port
from harp_apps.storage.utils.testing.sql import get_scoped_database_url

logger = get_logger(__name__)


class RunHarpProxyInSubprocessThread(threading.Thread):
    daemon = False

    def __init__(
        self,
        group=None,
        target=None,
        name=None,
        args=(),
        kwargs=None,
        *,
        daemon=None,
        config=None,
    ):
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.config_filename = None
        if config:
            with NamedTemporaryFile("w+", suffix=".yaml", delete=False) as _tmpfile_config:
                _tmpfile_config.write(config or "")
                self.config_filename = _tmpfile_config.name

        # XXX we may not need dev environment (yet maybe we want to test it works too). To avoid cryptic error, we
        # double check here to get an exception if not available.
        assert_development_packages_are_available()

    def run(self):
        command = [
            "harp",
            "start",
            "server",
            *(("--file", self.config_filename) if self.config_filename else ()),
            "--disable",
            "telemetry",
            "--disable",
            "dashboard",
        ]
        logger.info(f"Running command: {shlex.join(command)}")
        self.process = subprocess.Popen(command)

    def join(self, timeout=None):
        try:
            # try to kill gracefully ...
            self.process.terminate()
            self.process.wait(10.0)
        except Exception as e:
            logger.error(f"Error during process termination: {e}")
            self.process.kill()
        finally:
            # remove temporary config file ...
            if self.config_filename:
                os.unlink(self.config_filename)
            # ... and let threading handle the rest.
            super().join(timeout)
        logger.debug("Process terminated and joined successfully")


class AbstractProxyBenchmark:
    config = Template("")

    @pytest.fixture
    async def proxy(self, httpbin, database_url, test_id):
        async with get_scoped_database_url(database_url, test_id) as scoped_database_url:
            port = get_available_network_port()

            try:
                thread = RunHarpProxyInSubprocessThread(
                    config=self.config.substitute(port=port, httpbin=httpbin, database=scoped_database_url)
                )
            except Exception as exc:
                pytest.fail(f"Failed to create subprocess thread: {exc}")

            try:
                try:
                    from pytest_cov.embed import cleanup_on_sigterm
                except ImportError:
                    pass
                else:
                    cleanup_on_sigterm()
                thread.start()
                wait_for_port(port)
                yield f"localhost:{port}"
            finally:
                thread.join()

    def test_noproxy_get(self, benchmark, httpbin):
        @benchmark
        def result():
            return httpx.get(f"{httpbin}/get")

    def test_httpbin_get(self, benchmark, proxy):
        @benchmark
        def result():
            return httpx.get(f"http://{proxy}/get")
