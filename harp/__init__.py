import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__version__ = "0.2.1"

from ._logging import get_logger  # noqa: E402, isort: skip
from harp.factories.proxy import ProxyFactory  # noqa: E402

__all__ = [
    ProxyFactory,
    ROOT_DIR,
    __version__,
    get_logger,
]
