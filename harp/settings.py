"""
The Settings (:mod:`harp.settings`) module contains hardcoded configuration for Harp. This is probably only handy
for the young days of harp, and will be replaced by something less hard-coded later.

Contents
--------

"""

__title__ = "Settings"

import builtins
from os import environ

#: Pagination size for api endpoints
PAGE_SIZE = 40

#: Default timeout for http requests
DEFAULT_TIMEOUT = 30.0

#: Seconds a client may stay silent in the middle of a request before the server hangs up.
DEFAULT_CLIENT_READ_TIMEOUT = 30.0

#: Bytes per second a request body must average once the grace period is over.
DEFAULT_MIN_REQUEST_BODY_RATE = 1024

#: Seconds during which a request body is not held to the minimum rate.
DEFAULT_REQUEST_BODY_GRACE_PERIOD = 10.0

#: Largest request body, in bytes, a proxy endpoint accepts: 100 MiB.
DEFAULT_MAX_REQUEST_BODY_SIZE = 100 * 1024 * 1024

#: Force environment override (dev or prod)
HARP_ENV = environ.pop("HARP_ENV", None)
if HARP_ENV is not None:
    HARP_ENV = HARP_ENV.strip().lower()
    if HARP_ENV not in ("dev", "prod"):
        HARP_ENV = None


def is_test_context():
    return getattr(builtins, "__pytest__", False)
