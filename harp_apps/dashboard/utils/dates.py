from datetime import UTC, datetime, timedelta
from typing import List

from harp_apps.storage.types import TransactionsGroupedByTimeBucket


def get_start_datetime_from_range(range: str | None, *, now=None) -> datetime | None:
    """
    Generate a list of datetime objects from a range string.
    """
    if not range:
        return None
    now = now or datetime.now(UTC)
    if range == "1h":
        start_datetime = now - timedelta(hours=1)
    elif range == "24h":
        start_datetime = now - timedelta(hours=24)
    elif range == "7d":
        start_datetime = now - timedelta(days=7)
    elif range == "1m":
        start_datetime = now - timedelta(days=30)
    elif range == "1y":
        start_datetime = now - timedelta(days=365)
    else:
        raise ValueError(f"Unknown range: {range}")
    return start_datetime


def _truncate_datetime_for_time_bucket(dt: datetime, time_bucket: str = "day") -> datetime:
    """
    Truncate a datetime object to the given time bucket.
    """
    if time_bucket == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_bucket == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    elif time_bucket == "minute":
        return dt.replace(second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown time bucket: {time_bucket}")


def generate_continuous_time_range(
    discontinuous_transactions: List[TransactionsGroupedByTimeBucket],
    start_datetime=None,
    time_bucket: str = "day",
) -> List[TransactionsGroupedByTimeBucket]:
    """
    Generate a list of datetime objects from a range string.
    """
    # Generate a list of datetime objects from a range string
    start_datetime = start_datetime if start_datetime else discontinuous_transactions[0]["datetime"]
    start_datetime = _truncate_datetime_for_time_bucket(start_datetime, time_bucket)

    end_datetime = datetime.now(UTC)
    delta = timedelta(
        days=1 if time_bucket == "day" else 0,
        hours=1 if time_bucket == "hour" else 0,
        minutes=1 if time_bucket == "minute" else 0,
    )

    datetime_range = [start_datetime + i * delta for i in range(int((end_datetime - start_datetime) / delta) + 1)]

    # Fill missing data points
    continuous_transactions = []
    for t in datetime_range:
        if t in [d["datetime"] for d in discontinuous_transactions]:
            continuous_transactions.append([d for d in discontinuous_transactions if d["datetime"] == t][0])
        else:
            continuous_transactions.append(
                {
                    "datetime": t,
                    "count": None,
                    "errors": None,
                    "cached": 0,
                    "meanDuration": None,
                    "meanTpdex": None,
                }
            )
    return continuous_transactions
