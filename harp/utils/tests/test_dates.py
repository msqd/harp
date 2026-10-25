from datetime import UTC, date, datetime, timedelta, timezone

from harp.utils.dates import ensure_date, ensure_datetime


def test_ensure_date():
    assert ensure_date("2020-01-01") == date(2020, 1, 1)
    assert ensure_date(date(2020, 1, 1)) == date(2020, 1, 1)
    assert ensure_date(datetime(2020, 1, 1, 13, 37, 42)) == date(2020, 1, 1)
    assert ensure_date(None) is None


def test_ensure_datetime():
    assert ensure_datetime("2020-01-01 13:37:42.123456") == datetime(2020, 1, 1, 13, 37, 42, 123456)
    assert ensure_datetime(date(2020, 1, 1)) == datetime(2020, 1, 1)
    assert ensure_datetime(datetime(2020, 1, 1, 13, 37, 42)) == datetime(2020, 1, 1, 13, 37, 42)
    assert ensure_datetime(None) is None


def test_ensure_datetime_converts_an_aware_datetime():
    paris = timezone(timedelta(hours=2))
    assert ensure_datetime(datetime(2020, 1, 1, 14, 0, tzinfo=paris), UTC) == datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
