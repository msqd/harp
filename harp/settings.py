"""
The Settings (:mod:`harp.settings`) module contains hardcoded configuration for Harp. This is probably only handy
for the young days of harp, and will be replaced by something less hard-coded later.

Contents
--------

"""

__title__ = "Settings"

import builtins
from os import environ

from harp.utils.env import get_bool_from_env

#: Pagination size for api endpoints
PAGE_SIZE = 40

#: Default timeout for http requests
DEFAULT_TIMEOUT = 30.0

#: Force environment override (dev or prod)
HARP_ENV = environ.pop("HARP_ENV", None)
if HARP_ENV is not None:
    HARP_ENV = HARP_ENV.strip().lower()
    if HARP_ENV not in ("dev", "prod"):
        HARP_ENV = None

USE_PROMETHEUS = get_bool_from_env("USE_PROMETHEUS", False)


def is_test_context():
    return getattr(builtins, "__pytest__", False)
