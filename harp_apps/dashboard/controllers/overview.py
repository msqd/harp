from harp.asgi import ASGIRequest, ASGIResponse
from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.typing.storage import Storage
from harp.views import json

from ..utils.dates import generate_continuous_time_range, get_start_datetime_from_range

time_bucket_for_range = {
    "1h": "minute",
    "24h": "hour",
    "7d": "day",
    "1m": "day",
    "1y": "day",
}


@RouterPrefix("/api/overview")
class OverviewController(RoutingController):
    def __init__(self, *, storage: Storage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/")
    async def get_overview_data(self, request: ASGIRequest, response: ASGIResponse):
        # endpoint and range from request
        endpoint = request.query.get("endpoint")
        range = request.query.get("timeRange", "24h")

        # time buckets and start_datetime accordingly
        time_bucket = time_bucket_for_range.get(range, "day")
        start_datetime = get_start_datetime_from_range(range)

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
        transactions_by_date_list = generate_continuous_time_range(
            discontinuous_transactions=transactions_by_date_list, time_bucket=time_bucket, start_datetime=start_datetime
        )
        return json(
            {
                "transactions": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "count": transactions_count,
                "meanDuration": mean_duration,
                "timeRange": range,
            }
        )
