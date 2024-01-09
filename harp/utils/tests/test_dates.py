from datetime import date, datetime

from harp.utils.dates import ensure_date


def test_ensure_date():
    assert ensure_date("2020-01-01") == date(2020, 1, 1)
    assert ensure_date(date(2020, 1, 1)) == date(2020, 1, 1)
    assert ensure_date(datetime(2020, 1, 1, 13, 37, 42)) == date(2020, 1, 1)
