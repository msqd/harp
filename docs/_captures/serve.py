"""Run ``harp server`` with the clock frozen at :data:`docs._captures.seed.NOW`, so time-relative views are stable."""

import importlib.metadata
import sys

from freezegun import freeze_time
from packaging.version import Version

import harp
from docs._captures.seed import NOW

if __name__ == "__main__":
    # The git describe string of a dev checkout would end up in the header of every capture.
    harp.__version__ = Version(importlib.metadata.version("harp-proxy")).base_version

    from harp.commandline import entrypoint

    # real_asyncio keeps the event loop on the real monotonic clock, only wall-clock reads are frozen.
    with freeze_time(NOW, tick=True, real_asyncio=True):
        sys.exit(entrypoint())
