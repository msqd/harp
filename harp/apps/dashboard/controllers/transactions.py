import math

from harp import get_logger
from harp.core.asgi.messages import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.core.models.transactions import Transaction
from harp.core.views.json import json
from harp.protocols.storage import Storage
from harp.settings import PAGE_SIZE

from ..filters import TransactionEndpointFacet, TransactionMethodFacet, TransactionStatusFacet, flatten_facet_value

logger = get_logger(__name__)


class TransactionsController(RoutingController):
    prefix = "/api/transactions"

    def __init__(self, *, storage: Storage, handle_errors=True, router=None):
        self.storage = storage
        self.facets = {
            facet.name: facet
            for facet in (
                TransactionEndpointFacet(storage=self.storage),
                TransactionMethodFacet(),
                TransactionStatusFacet(),
            )
        }

        super().__init__(handle_errors=handle_errors, router=router)

    def configure(self):
        self.router.route(self.prefix + "/")(self.list)
        self.router.route(self.prefix + "/filters")(self.filters)
        self.router.route(self.prefix + "/{id}")(self.get)
        self.router.route(self.prefix + "/set_flag")(self.set_flag)

    async def filters(self, request: ASGIRequest, response: ASGIResponse):
        await self.facets["endpoint"].refresh()

        return json(
            {
                name: facet.filter(
                    flatten_facet_value(request.query.getall(name, [])),
                )
                for name, facet in self.facets.items()
            },
        )

    async def list(self, request: ASGIRequest, response: ASGIResponse):
        page = int(request.query.get("page", 1))
        if page < 1:
            page = 1

        cursor = str(request.query.get("cursor", ""))

        results = await self.storage.find_transactions(
            with_messages=True,
            filters={
                name: facet.get_filter(
                    flatten_facet_value(request.query.getall(name, [])),
                )
                for name, facet in self.facets.items()
            },
            page=page,
            cursor=cursor,
        )

        return json(
            {
                "items": list(map(Transaction.to_dict, results.items)),
                "pages": math.ceil(results.meta.get("total", 0) / PAGE_SIZE),
                "total": results.meta.get("total", 0),
                "perPage": PAGE_SIZE,
            }
        )

    async def get(self, request: ASGIRequest, response: ASGIResponse, id):
        transaction = await self.storage.get_transaction(id)
        if not transaction:
            response.status = 404
            return json({"error": "Transaction not found"})
        return json(transaction.to_dict())

    async def set_flag(self, request: ASGIRequest, response: ASGIResponse):
        transaction_id = request.query.get("transaction_id")
        flag_type = request.query.get("type")
        username = request.context.get("user") or "anonymous"
        self.storage.set_transaction_flag(transaction_id, username, flag_type)
        return json({"success": True})
