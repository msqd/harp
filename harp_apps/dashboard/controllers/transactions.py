import math

from harp import get_logger
from harp.controllers import GetHandler, RouteHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, JsonHttpResponse
from harp.models.transactions import Transaction
from harp.settings import PAGE_SIZE
from harp.views.json import json
from harp_apps.storage.models.flags import FLAGS_BY_NAME
from harp_apps.storage.types import IStorage

from ..filters import (
    TransactionEndpointFacet,
    TransactionFlagFacet,
    TransactionMethodFacet,
    TransactionStatusFacet,
    TransactionTpdexFacet,
)

logger = get_logger(__name__)


@RouterPrefix("/api/transactions")
class TransactionsController(RoutingController):
    def __init__(self, *, storage: IStorage, handle_errors=True, router=None):
        self.storage = storage
        self.facets = {
            facet.name: facet
            for facet in (
                TransactionEndpointFacet(storage=self.storage),
                TransactionMethodFacet(),
                TransactionStatusFacet(),
                TransactionFlagFacet(),
                TransactionTpdexFacet(),
            )
        }

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/filters")
    async def filters(self, request: HttpRequest):
        await self.facets["endpoint"].refresh()

        return json(
            {name: facet.filter_from_query(request.query) for name, facet in self.facets.items()},
        )

    @GetHandler("/")
    async def list(self, request: HttpRequest):
        page = int(request.query.get("page", 1))
        if page < 1:
            page = 1

        cursor = str(request.query.get("cursor", ""))

        results = await self.storage.get_transaction_list(
            with_messages=True,
            filters={name: facet.get_filter_from_query(request.query) for name, facet in self.facets.items()},
            page=page,
            cursor=cursor,
            username=request.extensions.get("user") or "anonymous",
            text_search=request.query.get("search", ""),
        )

        return json(
            {
                "items": list(map(Transaction.to_dict, results.items)),
                "pages": math.ceil(results.meta.get("total", 0) / PAGE_SIZE),
                "total": results.meta.get("total", 0),
                "perPage": PAGE_SIZE,
            }
        )

    @GetHandler("/{id}")
    async def get(self, request: HttpRequest, id):
        transaction = await self.storage.get_transaction(
            id,
            username=request.extensions.get("user") or "anonymous",
        )

        if not transaction:
            return JsonHttpResponse({"error": "Transaction not found"}, status=404)

        return JsonHttpResponse(transaction.to_dict())

    @RouteHandler("/{id}/flags/{flag}", methods=["PUT", "DELETE"])
    async def set_user_flag(self, request: HttpRequest, id, flag):
        username = request.extensions.get("user", None) or "anonymous"
        flag_id = FLAGS_BY_NAME.get(flag)

        await self.storage.set_user_flag(
            transaction_id=id,
            username=username,
            flag=flag_id,
            value=False if request.method == "DELETE" else True,
        )

        return JsonHttpResponse({"success": True})
