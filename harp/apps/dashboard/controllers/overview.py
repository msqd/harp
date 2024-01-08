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

        return json(
            {
                "dailyStats": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "transactions": {"count": transactions_count, "meanDuration": mean_duration},
            }
        )
