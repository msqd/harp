from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.core.views.json import json
from harp.protocols.storage import IStorage


class TransactionsController:
    prefix = "/api/transactions"

    def __init__(self, storage: IStorage):
        self.storage = storage

    def register(self, router):
        router.route(self.prefix + "/")(self.list)
        router.route(self.prefix + "/{transaction}")(self.get)

    async def list(self, request: ASGIRequest, response: ASGIResponse):
        transactions = []
        async for transaction in self.storage.find_transactions(with_messages=True):
            transactions.append(transaction)
        return json(
            {
                "items": list(map(Transaction.to_dict, transactions)),
                "total": len(transactions),
                "limit": 50,
                "offset": 0,
                "page": 1,
                "pages": 1,
            }
        )

    async def get(self, request: ASGIRequest, response: ASGIResponse, transaction):
        return json(
            {
                "@type": "transaction",
                "@id": transaction,
            }
        )
