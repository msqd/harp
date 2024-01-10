from datetime import datetime, timedelta
from functools import cached_property
from itertools import chain

from harp import get_logger
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.core.views.json import json
from harp.protocols.storage import Storage

logger = get_logger(__name__)


def _flatten_facet_value(values: list):
    return list(
        chain(
            *map(lambda x: x.split(","), values),
        ),
    )


class AbstractFacet:
    name = None
    choices = set()

    def __init__(self):
        self.meta = {}

    @cached_property
    def values(self):
        return [{"name": choice, "count": self.meta.get(choice, {}).get("count", None)} for choice in self.choices]

    def get_filter(self, raw_data: list):
        query_endpoints = self.choices.intersection(raw_data)
        return list(query_endpoints) if len(query_endpoints) else None

    def filter(self, raw_data: list):
        return {
            "values": self.values,
            "current": self.get_filter(raw_data),
        }


class FacetWithStorage(AbstractFacet):
    def __init__(self, *, storage: Storage):
        super().__init__()
        self.storage = storage


class TransactionEndpointFacet(FacetWithStorage):
    name = "endpoint"

    def __init__(self, *, storage: Storage):
        super().__init__(storage=storage)
        self.choices = set()
        self._refreshed_at = None

    async def refresh(self):
        if not self._refreshed_at or (self._refreshed_at < datetime.now() - timedelta(minutes=1)):
            self._refreshed_at = datetime.now()
            meta = await self.storage.get_facet_meta(self.name)
            self.choices = set(meta.keys())
            self.meta = {endpoint: {"count": count} for endpoint, count in meta.items()}


class TransactionMethodFacet(AbstractFacet):
    name = "method"
    choices = {"GET", "POST", "PUT", "DELETE", "PATCH"}


class TransactionStatusFacet(AbstractFacet):
    name = "status"
    choices = {"2xx", "3xx", "4xx", "5xx"}


class TransactionsController:
    prefix = "/api/transactions"

    def __init__(self, storage: Storage):
        self.storage = storage
        self.facets = {
            facet.name: facet
            for facet in (
                TransactionEndpointFacet(storage=self.storage),
                TransactionMethodFacet(),
                TransactionStatusFacet(),
            )
        }

    def register(self, router):
        router.route(self.prefix + "/")(self.list)
        router.route(self.prefix + "/filters")(self.filters)

    async def filters(self, request: ASGIRequest, response: ASGIResponse):
        await self.facets["endpoint"].refresh()

        return json(
            {
                name: facet.filter(
                    _flatten_facet_value(request.query.getall(name, [])),
                )
                for name, facet in self.facets.items()
            },
        )

    async def list(self, request: ASGIRequest, response: ASGIResponse):
        page = int(request.query.get("page", 1))
        if page < 1:
            page = 1

        cursor = str(request.query.get("cursor", ""))

        transactions = []
        async for transaction in self.storage.find_transactions(
            with_messages=True,
            filters={
                name: facet.get_filter(
                    _flatten_facet_value(request.query.getall(name, [])),
                )
                for name, facet in self.facets.items()
            },
            page=page,
            cursor=cursor,
        ):
            transactions.append(transaction)
        return json(
            {
                "items": list(map(Transaction.to_dict, transactions)),
                "total": len(transactions),
            }
        )
