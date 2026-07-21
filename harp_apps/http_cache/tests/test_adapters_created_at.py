"""The cache `created_at` field is written and read as GMT/UTC, independent of the host timezone."""

import os
import time
from contextlib import contextmanager

from harp_apps.http_cache.adapters import _format_created_at, _parse_created_at


@contextmanager
def _local_timezone(tz: str):
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = tz
    time.tzset()
    try:
        yield
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()


# 2023-11-14 22:13:20 UTC
_TS = 1_700_000_000.0
_GMT = "Tue, 14 Nov 2023 22:13:20 GMT"


def test_format_created_at_renders_utc():
    assert _format_created_at(_TS) == _GMT


def test_parse_created_at_reads_gmt_as_utc():
    assert _parse_created_at(_GMT) == _TS


def test_created_at_roundtrip_is_stable():
    assert _parse_created_at(_format_created_at(_TS)) == _TS


def test_created_at_is_utc_regardless_of_local_timezone():
    # The GMT string is a wire format: a non-UTC server must still write and read it as UTC,
    # otherwise the stored value is mislabeled and round-trips break across timezones.
    with _local_timezone("America/New_York"):
        assert _format_created_at(_TS) == _GMT
        assert _parse_created_at(_GMT) == _TS
        assert _parse_created_at(_format_created_at(_TS)) == _TS
