from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views import json
from harp.protocols.storage import IStorage

# from harp.apps.dashboard.schemas import TransactionsByDate


class OverviewController:
    prefix = "/api/overview"

    def __init__(self, storage: IStorage):
        self.storage = storage

    def register(self, router):
        router.route(self.prefix + "/")(self.get_overview_data)
        router.route(self.prefix + "/{endpoint}")(self.get_dashboard_data_for_endpoint)

    async def get_overview_data(self, request: ASGIRequest, response: ASGIResponse):
        transactions_by_date_list = await self.storage.transactions_grouped_by_date()
        errors_count = sum([t["errors"] for t in transactions_by_date_list])
        transactions_count = sum([t["transactions"] for t in transactions_by_date_list])
        errors_rate = errors_count / transactions_count if transactions_count else 0
        mean_duration = (
            sum([t["meanDuration"] * t["transactions"] for t in transactions_by_date_list]) / transactions_count
            if transactions_count
            else 0
        )

        return json(
            {
                "dailyStats": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "transactions": {"count": transactions_count, "meanDuration": mean_duration},
            }
        )

    async def get_dashboard_data_for_endpoint(self, request: ASGIRequest, response: ASGIResponse, endpoint: str):
        data_foo = [
            {"date": "2022-01-01", "transactions": 120, "errors": 100},
            {"date": "2022-01-02", "transactions": 160, "errors": 30},
            {"date": "2022-01-03", "transactions": 200, "errors": 40},
            {"date": "2022-01-04", "transactions": 100, "errors": 50},
            {"date": "2022-01-05", "transactions": 280, "errors": 60},
            {"date": "2022-01-06", "transactions": 320, "errors": 70},
            {"date": "2022-01-07", "transactions": 300, "errors": 50},
            {"date": "2022-01-08", "transactions": 400, "errors": 90},
            {"date": "2022-01-09", "transactions": 440, "errors": 50},
        ]
        data_bar = [
            {"date": "2022-01-01", "transactions": 120, "errors": 20},
            {"date": "2022-01-02", "transactions": 160, "errors": 30},
            {"date": "2022-01-03", "transactions": 200, "errors": 80},
            {"date": "2022-01-04", "transactions": 100, "errors": 50},
            {"date": "2022-01-05", "transactions": 280, "errors": 30},
            {"date": "2022-01-06", "transactions": 320, "errors": 10},
            {"date": "2022-01-07", "transactions": 300, "errors": 50},
            {"date": "2022-01-08", "transactions": 400, "errors": 50},
            {"date": "2022-01-10", "transactions": 440, "errors": 50},
        ]

        endpoints_data = {
            "foo": data_foo,
            "bar": data_bar,
        }

        return json(
            {
                "dailyStats": endpoints_data[endpoint],
                "errors": {"count": 100, "rate": 0.1},
                "transactions": {"count": 1000, "meanDuration": 0.1},
            }
        )
