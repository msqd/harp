"""
The Core (:mod:`harp`) package is the root namespace of the Harp framework.

It mostly contains a reference to the :class:`Config` class, because it's the only object you need to start using Harp
using the python API (you don't *need* to use this API, configuration files should be enough for most use cases, but
if you want to, this is the starting point).

For convenience, the :func:`run` function is also available, which is a simple way to start the default server
implementation for your configuration object.

Example usage:

.. code-block:: python

    from harp import Config, run

    config = Config()
    config.add_defaults()

    if __name__ == "__main__":
        run(config)

You can find more information about how configuration works in the :mod:`harp.config` module.

Contents
--------

"""

import os
from subprocess import check_output
from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from harp.config import ConfigurationBuilder as _ConfigurationBuilder


ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Debug mode flag. When enabled, HARP will output additional debugging information that may not be safe for
#: production environments (e.g., exception tracebacks in error responses). Set via HARP_DEBUG or DEBUG environment
#: variables.
DEBUG: bool = bool(os.environ.get("HARP_DEBUG") or os.environ.get("DEBUG"))


def get_relative_path(path: str) -> str:
    """
    Returns the relative path of the given path from the root directory.

    :param path: The path to get the relative path of.
    :return: The relative path.
    """
    return os.path.relpath(path, ROOT_DIR)


def _parse_version(version: str, /, *, default=None) -> Version:
    try:
        return Version(version)
    except InvalidVersion:
        if "-" in version:
            return _parse_version(version.rsplit("-", 1)[0], default=default)
        return default


# Version Detection Strategy
#
# HARP uses a three-layer version detection strategy:
#
# Layer 1 (Development): Git-based version
#   - Only active in development mode (git repo exists and not in CI)
#   - Uses `git describe` to provide detailed version info (e.g., "0.9.0-3-gd1234ab-dirty")
#   - Helps developers identify exact commits during debugging
#   - Disabled in CI to prevent git-based versions in documentation builds
#
# Layer 2 (Installed): Package metadata version
#   - Uses importlib.metadata to read version from installed package
#   - Ensures installed wheels report the correct version from pyproject.toml
#   - Works for both regular installs and editable installs
#
# Layer 3 (Fallback): Unknown version
#   - Used when both git and package metadata are unavailable
#   - Indicates an unusual setup that should be investigated

__title__ = "Core"
__version__ = "unknown"  # Fallback version
__hardcoded_version__ = __version__
__revision__ = __version__  # Will be set to git commit hash if available

# Layer 1: Git-based version (development mode)
if not os.environ.get("CI") and os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        # Use git describe for detailed version info (e.g., "0.9.0-3-gd1234ab-dirty")
        __version__ = (
            check_output(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT_DIR).decode("utf-8").strip()
        )
    except Exception:
        # Fallback to short commit hash if git describe fails
        __version__ = __revision__[:7]
else:
    # Layer 2: Installed package version
    try:
        import importlib.metadata

        __version__ = importlib.metadata.version("harp-proxy")
    except Exception:
        # Layer 3: Keep fallback version "unknown"
        pass

__parsed_version__ = _parse_version(__version__)

from ._logging import get_logger  # noqa: E402


async def arun(builder: "_ConfigurationBuilder"):
    from harp.config.adapters.hypercorn import HypercornAdapter

    system = await builder.abuild_system()
    server = HypercornAdapter(system)
    try:
        return await server.serve()
    finally:
        await system.dispose()


def run(builder: "_ConfigurationBuilder"):
    """
    Run the default server using provided configuration.

    :param builder: Config
    :return:
    """
    import asyncio

    return asyncio.run(arun(builder))


__all__ = [
    "DEBUG",
    "ROOT_DIR",
    "__revision__",
    "__version__",
    "__parsed_version__",
    "get_logger",
    "run",
]
