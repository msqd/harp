import math

from sqlalchemy.exc import NoResultFound

from harp.controllers import GetHandler, RouteHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, JsonHttpResponse
from harp.models.transactions import Transaction
from harp.security.actor import Role, get_actor
from harp.settings import PAGE_SIZE
from harp.views.json import json
from harp_apps.storage.models.flags import FLAGS_BY_NAME
from harp_apps.storage.types import IStorage

from ..filters import (
    TransactionCacheFacet,
    TransactionEndpointFacet,
    TransactionFlagFacet,
    TransactionMethodFacet,
    TransactionStatusFacet,
    TransactionTpdexFacet,
)


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
                TransactionCacheFacet(),
                TransactionFlagFacet(),
                TransactionTpdexFacet(),
            )
        }

        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/filters", role=Role.VIEWER)
    async def filters(self, request: HttpRequest):
        await self.facets["endpoint"].refresh()

        return json(
            {name: facet.filter_from_query(request.query) for name, facet in self.facets.items()},
        )

    @GetHandler("/", role=Role.VIEWER)
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
            username=get_actor(request).account.username,
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

    @GetHandler("/{id}", role=Role.VIEWER)
    async def get(self, request: HttpRequest, id):
        transaction = await self.storage.get_transaction(
            id,
            username=get_actor(request).account.username,
        )

        if not transaction:
            return JsonHttpResponse({"error": "Transaction not found"}, status=404)

        return JsonHttpResponse(transaction.to_dict())

    @RouteHandler("/{id}/flags/{flag}", methods=["PUT", "DELETE"], role=Role.VIEWER)
    async def set_user_flag(self, request: HttpRequest, id, flag):
        username = get_actor(request).account.username
        flag_id = FLAGS_BY_NAME.get(flag)
        if flag_id is None:
            return JsonHttpResponse({"error": "Unknown flag"}, status=400)

        try:
            await self.storage.set_user_flag(
                transaction_id=id,
                username=username,
                flag=flag_id,
                value=request.method != "DELETE",
            )
        except NoResultFound:
            return JsonHttpResponse({"error": "Transaction not found"}, status=404)

        return JsonHttpResponse({"success": True})
