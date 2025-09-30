import os
import shlex
import subprocess
import threading
import time
from string import Template
from tempfile import NamedTemporaryFile
from typing import List

import httpx
import pytest

from harp import get_logger
from harp.commandline.start import assert_development_packages_are_available
from harp.utils.network import _port_manager, get_reserved_port, wait_for_port
from harp_apps.storage.utils.testing.sql import get_scoped_database_url

logger = get_logger(__name__)


def get_adjusted_timeout(base_timeout: float = 10.0) -> float:
    """Adjust timeout based on system load.

    Args:
        base_timeout: Base timeout in seconds.

    Returns:
        Adjusted timeout value.
    """
    try:
        # Get system load average (1, 5, 15 minutes)
        load_avg = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 1

        # Calculate load factor (load per CPU)
        load_factor = load_avg / cpu_count

        # Adjust timeout based on load
        if load_factor < 1.5:
            return base_timeout
        elif load_factor < 3.0:
            return base_timeout * 1.5
        else:
            return min(base_timeout * 2.0, 30.0)
    except AttributeError:
        # Windows doesn't have getloadavg
        return base_timeout * 1.5


def start_subprocess_with_retry(
    command: List[str], max_retries: int = 3, retry_delay: float = 1.0, startup_check_delay: float = 0.5
) -> subprocess.Popen:
    """Start a subprocess with retry logic.

    Args:
        command: Command to execute.
        max_retries: Maximum number of retry attempts.
        retry_delay: Delay between retries in seconds.
        startup_check_delay: Delay before checking if process started successfully.

    Returns:
        The started subprocess.

    Raises:
        RuntimeError: If subprocess fails to start after max retries.
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting subprocess (attempt {attempt + 1}/{max_retries}): {shlex.join(command)}")
            process = subprocess.Popen(command)

            # Give the process time to start and check if it's still running
            time.sleep(startup_check_delay)
            poll_result = process.poll()
            if poll_result is None:
                logger.info("Subprocess started successfully")
                return process
            else:
                logger.warning(f"Subprocess exited with code {poll_result}")

        except Exception as e:
            logger.error(f"Failed to start subprocess: {e}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    raise RuntimeError(f"Failed to start subprocess after {max_retries} attempts")


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
        # Use harp-proxy instead of harp, and check if we're in a uv environment
        base_command = "harp-proxy"
        if os.environ.get("UV_PROJECT_ROOT") or os.path.exists(".venv/bin/harp-proxy"):
            # We're likely in a UV environment, use uv run
            command = ["uv", "run", base_command]
        else:
            command = [base_command]

        command.extend(
            [
                "server",
                *(("--file", self.config_filename) if self.config_filename else ()),
                "--disable",
                "telemetry",
                "--disable",
                "dashboard",
            ]
        )

        logger.info(f"Running command: {shlex.join(command)}")

        # Use retry logic for starting the subprocess
        try:
            self.process = start_subprocess_with_retry(command, max_retries=3, retry_delay=1.0, startup_check_delay=0.5)
        except RuntimeError as e:
            logger.error(f"Failed to start harp proxy subprocess: {e}")
            raise

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
            # Use port reservation to get an available port
            port = get_reserved_port()
            # Release it immediately so the subprocess can bind to it
            _port_manager.release_port(port)

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

                # Use dynamic timeout based on system load
                timeout = get_adjusted_timeout(base_timeout=10.0)
                wait_for_port(port, timeout=timeout)

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
