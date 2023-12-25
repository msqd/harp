from functools import cached_property
from random import randint

from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.core.views.json import json
from harp.protocols.storage import IStorage


class TransactionEndpointFacet:
    def __init__(self):
        self.endpoints = {"httpbin", "stripe", "twilio", "ban"}

    @cached_property
    def values(self):
        return [{"name": endpoint, "count": randint(20, 200)} for endpoint in self.endpoints]

    def get_filter(self, raw_data: list):
        query_endpoints = self.endpoints.intersection(raw_data)
        return list(query_endpoints) if len(query_endpoints) else "*"

    def filter(self, raw_data: list):
        return {
            "values": self.values,
            "current": self.get_filter(raw_data),
        }


class TransactionsController:
    prefix = "/api/transactions"

    def __init__(self, storage: IStorage):
        self.storage = storage
        self.facets = {"endpoint": TransactionEndpointFacet()}

    def register(self, router):
        router.route(self.prefix + "/")(self.list)
        router.route(self.prefix + "/filters")(self.filters)

    async def filters(self, request: ASGIRequest, response: ASGIResponse):
        return json(
            {name: facet.filter(request.query.getall(name, [])) for name, facet in self.facets.items()},
        )

    async def list(self, request: ASGIRequest, response: ASGIResponse):
        transactions = []
        async for transaction in self.storage.find_transactions(
            with_messages=True,
            filters={name: facet.get_filter(request.query.getall(name, [])) for name, facet in self.facets.items()},
        ):
            transactions.append(transaction)
        return json(
            {
                "items": list(map(Transaction.to_dict, transactions)),
                "total": len(transactions),
            }
        )
