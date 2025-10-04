"""Integration tests for UV and UVX execution of harp-proxy."""

import pytest
import subprocess
from pathlib import Path


def is_uv_available():
    """Check if UV is available in the system."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_uvx_available():
    """Check if UVX is available in the system."""
    try:
        subprocess.run(["uvx", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.mark.subprocess
@pytest.mark.skip
class TestUVIntegration:
    """Test UV integration for harp-proxy."""

    @pytest.mark.skipif(not is_uv_available(), reason="UV not available")
    def test_uv_run_harp_proxy_help(self):
        """Test running harp-proxy help with uv run."""
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "HTTP Application Runtime Proxy (HARP)" in result.stdout
        assert "server" in result.stdout
        assert "config" in result.stdout

    @pytest.mark.skipif(not is_uv_available(), reason="UV not available")
    def test_uv_run_harp_proxy_version(self):
        """Test running harp-proxy version with uv run."""
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "harp" in result.stdout.lower()

    @pytest.mark.skipif(not is_uv_available(), reason="UV not available")
    def test_uv_run_python_m_harp_help(self):
        """Test running python -m harp with uv run."""
        result = subprocess.run(
            ["uv", "run", "python", "-m", "harp", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "HTTP Application Runtime Proxy (HARP)" in result.stdout

    @pytest.mark.skipif(not is_uvx_available(), reason="UVX not available")
    def test_uvx_harp_proxy_help(self):
        """Test running harp-proxy help with uvx."""
        # First, we need to ensure the current project is installable
        # UVX will use the published package, so we test with --from
        project_path = Path(__file__).parent.parent
        result = subprocess.run(
            ["uvx", "--from", str(project_path), "harp-proxy", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "HTTP Application Runtime Proxy (HARP)" in result.stdout

    @pytest.mark.skipif(not is_uvx_available(), reason="UVX not available")
    def test_uvx_harp_proxy_version(self):
        """Test running harp-proxy version with uvx."""
        project_path = Path(__file__).parent.parent
        result = subprocess.run(
            ["uvx", "--from", str(project_path), "harp-proxy", "version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "harp" in result.stdout.lower()

    @pytest.mark.skipif(not is_uvx_available(), reason="UVX not available")
    def test_uvx_python_m_harp(self):
        """Test running python -m harp with uvx."""
        project_path = Path(__file__).parent.parent
        result = subprocess.run(
            ["uvx", "--from", str(project_path), "--with", "harp-proxy", "python", "-m", "harp", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "HTTP Application Runtime Proxy (HARP)" in result.stdout

    @pytest.mark.skipif(not is_uv_available(), reason="UV not available")
    def test_uv_run_harp_proxy_config(self):
        """Test running harp-proxy config with uv run."""
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "config", "--example", "sqlite"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "📦 applications" in result.stdout
        assert "📦 storage" in result.stdout
        assert "harp_apps.proxy" in result.stdout

    @pytest.mark.skipif(not is_uv_available(), reason="UV not available")
    def test_uv_run_harp_proxy_examples_list(self):
        """Test running harp-proxy examples list with uv run."""
        result = subprocess.run(
            ["uv", "run", "harp-proxy", "examples", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "sqlite" in result.stdout
        assert "proxy:httpbin" in result.stdout
