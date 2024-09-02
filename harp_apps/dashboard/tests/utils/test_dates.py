from datetime import UTC, datetime, timedelta
from typing import List
from unittest.mock import patch

import pytest

from harp_apps.dashboard.utils.dates import (
    _truncate_datetime_for_time_bucket,
    generate_continuous_time_range,
    get_start_datetime_from_range,
)
from harp_apps.storage.types import TransactionsGroupedByTimeBucket


def test_get_start_datetime_from_range():
    now = datetime.now(UTC)
    start_datetime = get_start_datetime_from_range("1h")
    assert start_datetime is not None and abs((start_datetime - (now - timedelta(hours=1))).total_seconds()) < 1
    start_datetime = get_start_datetime_from_range("24h")
    assert start_datetime is not None and abs((start_datetime - (now - timedelta(hours=24))).total_seconds()) < 1
    start_datetime = get_start_datetime_from_range("7d")
    assert start_datetime is not None and abs((start_datetime - (now - timedelta(days=7))).total_seconds()) < 1
    start_datetime = get_start_datetime_from_range("1m")
    assert start_datetime is not None and abs((start_datetime - (now - timedelta(days=30))).total_seconds()) < 1
    start_datetime = get_start_datetime_from_range("1y")
    assert start_datetime is not None and abs((start_datetime - (now - timedelta(days=365))).total_seconds()) < 1
    assert get_start_datetime_from_range(None) is None
    with pytest.raises(ValueError):
        get_start_datetime_from_range("unknown")


def test__truncate_datetime_for_time_bucket():
    dt = datetime(2022, 1, 1, 12, 34, 56, 789000, tzinfo=UTC)
    assert _truncate_datetime_for_time_bucket(dt, "day") == datetime(2022, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
    assert _truncate_datetime_for_time_bucket(dt, "hour") == datetime(2022, 1, 1, 12, 0, 0, 0, tzinfo=UTC)


def test_generate_continuous_time_range():
    discontinuous_transactions: List[TransactionsGroupedByTimeBucket]
    discontinuous_transactions = [
        {
            "datetime": datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),
            "count": 10,
            "errors": 0,
            "meanDuration": 1.0,
        },
        {
            "datetime": datetime(2022, 1, 1, 2, 0, 0, tzinfo=UTC),
            "count": 20,
            "errors": 1,
            "meanDuration": 1.5,
        },
    ]
    start_datetime = datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC)
    time_bucket = "hour"
    with patch("harp_apps.dashboard.utils.dates.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2022, 1, 1, 7, 0, 0, tzinfo=UTC)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        result = generate_continuous_time_range(discontinuous_transactions, start_datetime, time_bucket)

    assert len(result) == 8
    assert result[0]["datetime"] == start_datetime
    assert result[0]["count"] == 10
    assert result[0]["errors"] == 0
    assert result[0]["meanDuration"] == 1.0
    assert result[1]["datetime"] == start_datetime + timedelta(hours=1)
    assert result[1]["count"] is None
    assert result[1]["errors"] is None
    assert result[1]["meanDuration"] is None
    assert result[2]["datetime"] == start_datetime + timedelta(hours=2)
    assert result[2]["count"] == 20
    assert result[2]["errors"] == 1
    assert result[2]["meanDuration"] == 1.5


def test_generate_continuous_time_range_from_empty_discontinuous():
    discontinuous_transactions: List[TransactionsGroupedByTimeBucket]
    discontinuous_transactions = []

    start_datetime = datetime(2022, 1, 1, tzinfo=UTC)
    time_bucket = "hour"
    with patch("harp_apps.dashboard.utils.dates.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2022, 1, 1, 7, 0, 0, tzinfo=UTC)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        result = generate_continuous_time_range(discontinuous_transactions, start_datetime, time_bucket)

    assert len(result) == 8
