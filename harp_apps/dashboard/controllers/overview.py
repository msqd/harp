from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import StatisticsError, mean

from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest
from harp.views import json
from harp_apps.storage.constants import TimeBucket
from harp_apps.storage.types import IStorage

from ..utils.dates import generate_continuous_time_range, get_start_datetime_from_range

time_bucket_for_range = {
    "1h": TimeBucket.HOUR.value,
    "24h": TimeBucket.HOUR.value,
    "7d": TimeBucket.DAY.value,
    "1m": TimeBucket.DAY.value,
    "1y": TimeBucket.DAY.value,
}


def _format_aggregate(items, count, key, *, default=None):
    if count >= 86400:
        period = "sec"
        divider = 86400

    elif count >= 1440:
        period = "min"
        divider = 1440

    elif count >= 24:
        period = "hour"
        divider = 24

    else:
        period = "day"
        divider = 1

    return {
        "rate": Decimal(int(10 * (count / divider))) / 10,
        "period": period,
        "data": [
            {
                "datetime": t["datetime"],
                "value": int(t[key]) if t[key] is not None else default,
            }
            for t in items
        ],
    }


@RouterPrefix("/api/overview")
class OverviewController(RoutingController):
    def __init__(self, *, storage: IStorage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/summary")
    async def get_summary_data(self, request: HttpRequest):
        time_span = "24h"
        time_bucket = time_bucket_for_range[time_span]
        now = datetime.now(UTC)
        start_datetime = get_start_datetime_from_range(time_span, now=now + timedelta(hours=1))

        transactions_by_date_list = await self.storage.transactions_grouped_by_time_bucket(
            start_datetime=start_datetime, time_bucket=time_bucket
        )

        errors_count = sum([t["errors"] for t in transactions_by_date_list])
        transactions_count = sum([t["count"] for t in transactions_by_date_list])

        transactions_by_date_list = generate_continuous_time_range(
            discontinuous_transactions=transactions_by_date_list,
            time_bucket=time_bucket,
            start_datetime=start_datetime,
        )
        try:
            mean_tpdex = mean(filter(None, [t["meanTpdex"] for t in transactions_by_date_list]))
        except StatisticsError:
            mean_tpdex = 100

        return json(
            {
                "tpdex": {
                    "mean": int(mean_tpdex),
                    "data": [
                        {
                            "datetime": t["datetime"],
                            "value": (int(t["meanTpdex"]) if t["meanTpdex"] is not None else 100),
                        }
                        for t in transactions_by_date_list
                    ],
                },
                "transactions": _format_aggregate(transactions_by_date_list, transactions_count, "count", default=0),
                "errors": _format_aggregate(transactions_by_date_list, errors_count, "errors", default=0),
            }
        )

    @GetHandler("/")
    async def get_overview_data(self, request: HttpRequest):
        # endpoint and range from request
        endpoint = request.query.get("endpoint")
        range = request.query.get("timeRange", "24h")

        # time buckets and start_datetime accordingly
        time_bucket = time_bucket_for_range.get(range, "day")
        start_datetime = get_start_datetime_from_range(range)

        transactions_by_date_list = await self.storage.transactions_grouped_by_time_bucket(
            endpoint=endpoint,
            start_datetime=start_datetime,
            time_bucket=time_bucket,
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
            discontinuous_transactions=transactions_by_date_list,
            time_bucket=time_bucket,
            start_datetime=start_datetime,
        )

        try:
            mean_tpdex = mean(filter(None, [t["meanTpdex"] for t in transactions_by_date_list]))
        except StatisticsError:
            mean_tpdex = 100

        return json(
            {
                "transactions": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "count": transactions_count,
                "meanDuration": mean_duration,
                "meanTpdex": mean_tpdex,
                "timeRange": range,
            }
        )
