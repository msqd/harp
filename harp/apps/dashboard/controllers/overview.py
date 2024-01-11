from datetime import timedelta
from typing import List

from harp.core.asgi.messages import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.core.views import json
from harp.protocols.storage import Storage, TransactionsGroupedByDate

# from harp.apps.dashboard.schemas import TransactionsByDate


class OverviewController(RoutingController):
    prefix = "/api/overview"

    def __init__(self, *, storage: Storage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    def configure(self):
        self.router.route(self.prefix + "/")(self.get_overview_data)

    async def get_overview_data(self, request: ASGIRequest, response: ASGIResponse):
        endpoint = request.query.get("endpoint")
        transactions_by_date_list = await self.storage.transactions_grouped_by_date(endpoint=endpoint)
        errors_count = sum([t["errors"] for t in transactions_by_date_list])
        transactions_count = sum([t["transactions"] for t in transactions_by_date_list])
        errors_rate = errors_count / transactions_count if transactions_count else 0
        mean_duration = (
            sum([t["meanDuration"] * t["transactions"] for t in transactions_by_date_list]) / transactions_count
            if transactions_count
            else 0
        )
        transactions_by_date_list = _fill_missing_data_points(transactions_by_date_list)
        return json(
            {
                "dailyStats": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "transactions": {"count": transactions_count, "meanDuration": mean_duration},
            }
        )


def _fill_missing_data_points(
    transactions_by_date_list: List[TransactionsGroupedByDate],
) -> List[TransactionsGroupedByDate]:
    """
    Fill missing data points in the transactions_by_date_list.
    """
    if not transactions_by_date_list:
        return transactions_by_date_list

    # Fill missing data points
    start_date = transactions_by_date_list[0]["date"]
    date = start_date
    filled_transactions_by_date_list = []
    for t in transactions_by_date_list:
        while date < t["date"]:
            filled_transactions_by_date_list.append(
                {"date": date, "transactions": None, "errors": None, "meanDuration": None}
            )
            date += timedelta(days=1)
        filled_transactions_by_date_list.append(t)
        date += timedelta(days=1)
    return filled_transactions_by_date_list
