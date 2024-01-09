from datetime import timedelta
from typing import List

from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views import json
from harp.protocols.storage import Storage, TransactionsGroupedByTimeBucket

# from harp.apps.dashboard.schemas import TransactionsByDate


class OverviewController:
    prefix = "/api/overview"

    def __init__(self, storage: Storage):
        self.storage = storage

    def register(self, router):
        router.route(self.prefix + "/")(self.get_overview_data)

    async def get_overview_data(self, request: ASGIRequest, response: ASGIResponse):
        endpoint = request.query.get("endpoint")
        tb = request.query.get("timeBucket", "hour")
        transactions_by_date_list = await self.storage.transactions_grouped_by_time_bucket(
            endpoint=endpoint, time_bucket=tb
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
            discontinuous_transactions=transactions_by_date_list, time_bucket=tb
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
    discontinuous_transactions: List[TransactionsGroupedByTimeBucket], time_bucket: str = "day"
) -> List[TransactionsGroupedByTimeBucket]:
    """
    Generate a list of datetime objects from a range string.
    """
    if not discontinuous_transactions:
        return discontinuous_transactions

    # Generate a list of datetime objects from a range string
    start_datetime = discontinuous_transactions[0]["datetime"]
    end_datetime = discontinuous_transactions[-1]["datetime"]
    delta = timedelta(
        days=1 if time_bucket == "day" else 0,
        hours=1 if time_bucket == "hour" else 0,
        minutes=1 if time_bucket == "minute" else 0,
        seconds=1 if time_bucket == "second" else 0,
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
