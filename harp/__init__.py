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


def _parse_version(version: str, /, *, default=None) -> Version:
    try:
        return Version(version)
    except InvalidVersion:
        if "-" in version:
            return _parse_version(version.rsplit("-", 1)[0], default=default)
        return default


# last release
__title__ = "Core"
__version__ = "0.7.2"
__hardcoded_version__ = __version__
__revision__ = __version__  # we can't commit the not yet known revision

# override with version.txt if available (after docker build for example)
if os.path.exists(os.path.join(ROOT_DIR, "version.txt")):
    with open(os.path.join(ROOT_DIR, "version.txt")) as f:
        __version__ = f.read().strip()

__parsed_version__ = _parse_version(__version__)

# override with current development version/revision if available (disabled in CI, for docs)
if not os.environ.get("CI", False) and os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        __version__ = (
            check_output(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT_DIR).decode("utf-8").strip()
        )
        __parsed_version__ = _parse_version(__version__, default=__parsed_version__)
    except Exception:
        __version__ = __revision__[:7]

from ._logging import get_logger  # noqa: E402, isort: skip


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
    "ROOT_DIR",
    "__revision__",
    "__version__",
    "__parsed_version__",
    "get_logger",
    "run",
]
