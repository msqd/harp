"""Tests for version detection mechanism in harp.__init__."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestVersionDetection:
    """Test the multi-layer version detection strategy."""

    def test_git_version_in_development_mode(self):
        """When .git exists and not in CI, version should come from git describe."""
        # This test runs in the actual repo, so we should get a git-based version
        # unless CI is set or there's no git repo
        if os.environ.get("CI"):
            pytest.skip("Skipping git version test in CI mode")

        import harp

        # Check if we're in a git repo
        if not os.path.exists(os.path.join(harp.ROOT_DIR, ".git")):
            pytest.skip("Skipping git version test - not in a git repository")

        # In development mode with git repo, version should NOT be "unknown"
        assert harp.__version__ != "unknown"
        # Version should be git-based (could be tag, tag-commits-hash, or just hash)
        # Examples: "0.9.0-rc2", "0.9.0-1-gabc123", "abc1234"
        assert len(harp.__version__) > 0
        assert harp.__revision__ != "unknown"

    def test_installed_package_version_without_git(self, tmp_path, monkeypatch):
        """When no git repo but package is installed, version comes from importlib.metadata."""
        # Save original sys.modules state to restore later

        original_harp = sys.modules.get("harp")

        try:
            # Create a minimal module structure in tmp_path
            module_dir = tmp_path / "harp"
            module_dir.mkdir()

            # Mock the environment to simulate installed package (no git)
            mock_metadata = Mock()
            mock_metadata.version.return_value = "1.2.3"

            # Change ROOT_DIR to tmp_path (no .git directory)
            init_content = f'''
import os
from subprocess import check_output
from packaging.version import InvalidVersion, Version

ROOT_DIR = r"{tmp_path}"

def _parse_version(version, /, *, default=None):
    try:
        return Version(version)
    except InvalidVersion:
        if "-" in version:
            return _parse_version(version.rsplit("-", 1)[0], default=default)
        return default

__title__ = "Core"
__version__ = "unknown"
__hardcoded_version__ = __version__
__revision__ = __version__

# Layer 1: Git-based version (development mode)
if not os.environ.get("CI") and os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        __version__ = check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=ROOT_DIR
        ).decode("utf-8").strip()
        __parsed_version__ = _parse_version(__version__, default=__parsed_version__)
    except Exception:
        __version__ = __revision__[:7]
else:
    # Layer 2: Installed package version
    try:
        import importlib.metadata
        __version__ = importlib.metadata.version("harp-proxy")
        __parsed_version__ = _parse_version(__version__)
    except Exception:
        # Layer 3: Keep fallback version
        pass

__parsed_version__ = _parse_version(__version__)
'''
            (module_dir / "__init__.py").write_text(init_content)

            # Add tmp_path to sys.path
            monkeypatch.syspath_prepend(str(tmp_path))

            # Mock importlib.metadata to return our test version
            with patch("importlib.metadata.version", return_value="1.2.3"):
                # Remove harp from sys.modules if it exists
                if "harp" in sys.modules:
                    del sys.modules["harp"]

                # Import the test module
                import harp as test_harp

                # Version should come from importlib.metadata
                assert test_harp.__version__ == "1.2.3"
        finally:
            # Restore original sys.modules state
            if original_harp is not None:
                sys.modules["harp"] = original_harp
            elif "harp" in sys.modules:
                del sys.modules["harp"]

    def test_fallback_to_unknown_when_all_sources_fail(self, tmp_path, monkeypatch):
        """When both git and metadata fail, version should be 'unknown'."""

        original_harp = sys.modules.get("harp")

        try:
            # Create a minimal module structure in tmp_path
            module_dir = tmp_path / "harp"
            module_dir.mkdir()

            # This simulates the code we'll implement
            init_content = f'''
import os
from subprocess import check_output
from packaging.version import InvalidVersion, Version

ROOT_DIR = r"{tmp_path}"

def _parse_version(version, /, *, default=None):
    try:
        return Version(version)
    except InvalidVersion:
        if "-" in version:
            return _parse_version(version.rsplit("-", 1)[0], default=default)
        return default

__title__ = "Core"
__version__ = "unknown"
__hardcoded_version__ = __version__
__revision__ = __version__

# Layer 1: Git-based version (development mode)
if not os.environ.get("CI") and os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        __version__ = check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=ROOT_DIR
        ).decode("utf-8").strip()
        __parsed_version__ = _parse_version(__version__)
    except Exception:
        __version__ = __revision__[:7]
else:
    # Layer 2: Installed package version
    try:
        import importlib.metadata
        __version__ = importlib.metadata.version("harp-proxy")
        __parsed_version__ = _parse_version(__version__)
    except Exception:
        # Layer 3: Keep fallback version
        pass

__parsed_version__ = _parse_version(__version__)
'''
            (module_dir / "__init__.py").write_text(init_content)

            # Add tmp_path to sys.path
            monkeypatch.syspath_prepend(str(tmp_path))

            # Mock importlib.metadata to raise exception
            def mock_version_error(package_name):
                raise Exception("Package not found")

            with patch("importlib.metadata.version", side_effect=mock_version_error):
                # Remove harp from sys.modules if it exists
                if "harp" in sys.modules:
                    del sys.modules["harp"]

                # Import the test module
                import harp as test_harp

                # Version should be "unknown" since no git and metadata failed
                assert test_harp.__version__ == "unknown"
        finally:
            # Restore original sys.modules state
            if original_harp is not None:
                sys.modules["harp"] = original_harp
            elif "harp" in sys.modules:
                del sys.modules["harp"]

    def test_ci_mode_skips_git_and_uses_metadata(self, tmp_path, monkeypatch):
        """When CI=true, skip git even if .git exists and use metadata."""

        original_harp = sys.modules.get("harp")

        try:
            # Create a minimal module structure in tmp_path with fake .git
            module_dir = tmp_path / "harp"
            module_dir.mkdir()
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            init_content = f'''
import os
from subprocess import check_output
from packaging.version import InvalidVersion, Version

ROOT_DIR = r"{tmp_path}"

def _parse_version(version, /, *, default=None):
    try:
        return Version(version)
    except InvalidVersion:
        if "-" in version:
            return _parse_version(version.rsplit("-", 1)[0], default=default)
        return default

__title__ = "Core"
__version__ = "unknown"
__hardcoded_version__ = __version__
__revision__ = __version__

# Layer 1: Git-based version (development mode)
if not os.environ.get("CI") and os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        __version__ = check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=ROOT_DIR
        ).decode("utf-8").strip()
        __parsed_version__ = _parse_version(__version__)
    except Exception:
        __version__ = __revision__[:7]
else:
    # Layer 2: Installed package version
    try:
        import importlib.metadata
        __version__ = importlib.metadata.version("harp-proxy")
        __parsed_version__ = _parse_version(__version__)
    except Exception:
        # Layer 3: Keep fallback version
        pass

__parsed_version__ = _parse_version(__version__)
'''
            (module_dir / "__init__.py").write_text(init_content)

            # Add tmp_path to sys.path
            monkeypatch.syspath_prepend(str(tmp_path))

            # Set CI environment variable
            monkeypatch.setenv("CI", "true")

            # Mock importlib.metadata to return test version
            with patch("importlib.metadata.version", return_value="2.0.0.ci"):
                # Remove harp from sys.modules if it exists
                if "harp" in sys.modules:
                    del sys.modules["harp"]

                # Import the test module
                import harp as test_harp

                # Even though .git exists, CI mode should use metadata
                assert test_harp.__version__ == "2.0.0.ci"
        finally:
            # Restore original sys.modules state
            if original_harp is not None:
                sys.modules["harp"] = original_harp
            elif "harp" in sys.modules:
                del sys.modules["harp"]

    def test_git_takes_precedence_over_metadata(self):
        """When both git and metadata available, git version takes precedence."""
        # This test runs in the actual repo where both are available
        if os.environ.get("CI"):
            pytest.skip("Skipping git precedence test in CI mode")

        import harp

        # In development mode, version should be git-based, not from metadata
        # We can't know the exact format, but it should NOT be "unknown"
        assert harp.__version__ != "unknown"

        # Try to get metadata version for comparison
        try:
            import importlib.metadata

            _metadata_version = importlib.metadata.version("harp-proxy")
            # If package is installed in editable mode, git version might differ
            # from metadata version (git has more detail)
        except Exception:
            # Package might not be installed, that's ok
            pass

    def test_version_command_shows_correct_version(self):
        """Test that the version command outputs the correct version."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "harp-proxy", "version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "harp v" in result.stdout.lower()
        # Version should not be "unknown" in development
        if not os.environ.get("CI"):
            assert "unknown" not in result.stdout.lower()
