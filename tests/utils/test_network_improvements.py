import time

import pytest
import socket
import threading
from harp.utils.network import (
    PortReservationManager,
    get_reserved_port,
    wait_for_service_ready,
)
from unittest.mock import Mock, patch


class TestPortReservation:
    """Test improved port allocation with reservation mechanism."""

    def test_get_reserved_port_returns_available_port(self):
        """Test that get_reserved_port returns an available port."""
        port = get_reserved_port()
        assert isinstance(port, int)
        assert 1024 < port < 65535

    def test_reserved_port_stays_reserved(self):
        """Test that a reserved port cannot be immediately reused."""
        manager = PortReservationManager()
        port = manager.reserve_port()

        # Try to bind to the reserved port - should fail
        with pytest.raises(OSError):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("localhost", port))
            sock.close()

    def test_port_released_after_context_exit(self):
        """Test that port is released when context manager exits."""
        manager = PortReservationManager()

        with manager.reserve_port_context() as port:
            # Port should be reserved inside context
            assert port in manager._reserved_ports

        # Port should be released after context
        assert port not in manager._reserved_ports

        # Should be able to bind to it now
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", port))
        sock.close()

    def test_concurrent_port_reservation(self):
        """Test that concurrent threads get different ports."""
        manager = PortReservationManager()
        ports = []

        def reserve_port():
            port = manager.reserve_port()
            ports.append(port)
            time.sleep(0.1)  # Hold the port briefly
            manager.release_port(port)

        threads = [threading.Thread(target=reserve_port) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All ports should be unique
        assert len(set(ports)) == len(ports)


class TestServiceHealthCheck:
    """Test health checking beyond simple port availability."""

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_checks_health_endpoint(self):
        """Test that wait_for_service_ready polls health endpoint."""
        # Use a simple counter to track health check attempts
        check_count = 0

        async def mock_health_check(port):
            nonlocal check_count
            check_count += 1
            # Succeed on third attempt
            return check_count >= 3

        await wait_for_service_ready(port=8080, custom_check=mock_health_check, timeout=5.0)

        assert check_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_timeout(self):
        """Test that wait_for_service_ready times out appropriately."""
        with patch("harp.utils.network.httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection refused")

            with pytest.raises(TimeoutError, match="Service not ready"):
                await wait_for_service_ready(port=8080, health_path="/health", timeout=0.5)

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_custom_check(self):
        """Test custom readiness check function."""
        check_count = 0

        async def custom_check(port):
            nonlocal check_count
            check_count += 1
            if check_count < 3:
                return False
            return True

        await wait_for_service_ready(port=8080, custom_check=custom_check, timeout=5.0)

        assert check_count == 3


class TestSubprocessRetry:
    """Test subprocess startup retry logic."""

    def test_subprocess_start_with_retry(self):
        """Test that subprocess startup retries on failure."""
        from harp.utils.testing.subprocess import start_subprocess_with_retry

        mock_popen = Mock()
        mock_process = Mock()
        mock_process.poll.side_effect = [
            1,
            None,
        ]  # Fail once, then succeed (None means running)
        mock_popen.return_value = mock_process

        with patch("subprocess.Popen", mock_popen):
            process = start_subprocess_with_retry(
                ["harp-proxy", "server"],
                max_retries=3,
                retry_delay=0.01,
                startup_check_delay=0.01,
            )

            assert mock_popen.call_count == 2  # First attempt fails, second succeeds
            assert process == mock_process

    def test_subprocess_start_exceeds_retries(self):
        """Test that subprocess raises after max retries."""
        from harp.utils.testing.subprocess import start_subprocess_with_retry

        mock_popen = Mock()
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Always fail
        mock_popen.return_value = mock_process

        with patch("subprocess.Popen", mock_popen):
            with pytest.raises(RuntimeError, match="Failed to start subprocess"):
                start_subprocess_with_retry(["harp-proxy", "server"], max_retries=2, retry_delay=0.1)

            assert mock_popen.call_count == 2


class TestDynamicTimeout:
    """Test dynamic timeout adjustment based on system load."""

    def test_get_adjusted_timeout_normal_load(self):
        """Test timeout adjustment under normal load."""
        from harp.utils.testing.time import get_adjusted_timeout

        with patch("os.getloadavg", return_value=(1.0, 1.0, 1.0)):
            timeout = get_adjusted_timeout(base_timeout=10.0)
            assert timeout == 10.0  # No adjustment for low load

    def test_get_adjusted_timeout_high_load(self):
        """Test timeout adjustment under high load."""
        from harp.utils.testing.time import get_adjusted_timeout

        with patch("os.getloadavg", return_value=(8.0, 7.0, 6.0)):
            with patch("os.cpu_count", return_value=4):
                timeout = get_adjusted_timeout(base_timeout=10.0)
                assert timeout > 10.0  # Should increase under high load
                assert timeout <= 30.0  # But have a reasonable cap

    def test_get_adjusted_timeout_windows(self):
        """Test timeout adjustment on Windows (no getloadavg)."""
        from harp.utils.testing.time import get_adjusted_timeout

        with patch("os.getloadavg", side_effect=AttributeError):
            timeout = get_adjusted_timeout(base_timeout=10.0)
            assert timeout == 15.0  # Default multiplier for Windows
