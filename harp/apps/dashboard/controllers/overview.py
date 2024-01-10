from datetime import UTC, datetime, timedelta
from typing import List

from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views import json
from harp.protocols.storage import Storage, TransactionsGroupedByTimeBucket

# from harp.apps.dashboard.schemas import TransactionsByDate


time_bucket_for_range = {
    "1h": "minute",
    "24h": "hour",
    "7j": "day",
    "1m": "day",
}


class OverviewController:
    prefix = "/api/overview"

    def __init__(self, storage: Storage):
        self.storage = storage

    def register(self, router):
        router.route(self.prefix + "/")(self.get_overview_data)

    async def get_overview_data(self, request: ASGIRequest, response: ASGIResponse):
        # endpoint and range from request
        endpoint = request.query.get("endpoint")
        range = request.query.get("range", "24h")

        # time buckets and start_datetime accordingly
        time_bucket = time_bucket_for_range.get(range, "day")
        start_datetime = _start_and_end_datetimes_from_range(range)

        transactions_by_date_list = await self.storage.transactions_grouped_by_time_bucket(
            endpoint=endpoint, start_datetime=start_datetime, time_bucket=time_bucket
        )
        errors_count = sum([t["errors"] for t in transactions_by_date_list])
        transactions_count = sum([t["count"] for t in transactions_by_date_list])
        errors_rate = errors_count / transactions_count if transactions_count else 0
        mean_duration = (
            sum([t["meanDuration"] * t["count"] for t in transactions_by_date_list]) / transactions_count
            if transactions_count
            else 0
        )
        transactions_by_date_list = _generate_continuous_range(
            discontinuous_transactions=transactions_by_date_list, time_bucket=time_bucket, start_datetime=start_datetime
        )
        return json(
            {
                "transactions": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "count": transactions_count,
                "meanDuration": mean_duration,
            }
        )


def _generate_continuous_range(
    discontinuous_transactions: List[TransactionsGroupedByTimeBucket],
    start_datetime=None,
    time_bucket: str = "day",
) -> List[TransactionsGroupedByTimeBucket]:
    """
    Generate a list of datetime objects from a range string.
    """
    if not discontinuous_transactions:
        return discontinuous_transactions

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
            continuous_transactions.append({"datetime": t, "count": None, "errors": None, "meanDuration": None})
    return continuous_transactions


def _start_and_end_datetimes_from_range(range: str | None) -> datetime | None:
    """
    Generate a list of datetime objects from a range string.
    """
    if not range:
        return None
    now = datetime.now(UTC)
    if range == "1h":
        start_datetime = now - timedelta(hours=1)
    elif range == "24h":
        start_datetime = now - timedelta(hours=24)
    elif range == "7j":
        start_datetime = now - timedelta(days=7)
    elif range == "1m":
        start_datetime = now - timedelta(days=30)
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
