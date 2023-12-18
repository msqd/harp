import os
from subprocess import check_output

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# last release
__version__ = "0.2.2"
__revision__ = __version__  # we can't commit the not yet known revision

# override with current development version/revision if available
if os.path.exists(os.path.join(ROOT_DIR, ".git")):
    __revision__ = check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR).decode("utf-8").strip()
    try:
        __version__ = (
            check_output(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT_DIR).decode("utf-8").strip()
        )
    except Exception:
        __version__ = __revision__[:7]

from ._logging import get_logger  # noqa: E402, isort: skip
from harp.factories.proxy import ProxyFactory  # noqa: E402

__all__ = [
    ProxyFactory,
    ROOT_DIR,
    __version__,
    __revision__,
    get_logger,
]
