from http_router import NotFoundError, Router

from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.requests import ASGIRequest
from harp.core.asgi.responders import ASGIResponder
from harp.core.views.json import json


class Storage:
    async def find_transactions(self):
        import aiosqlite

        from harp.contrib.sqlite_storage.connect import connect_to_sqlite

        async with connect_to_sqlite() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 50") as cursor:
                async for row in cursor:
                    yield dict(row)


class DashboardController(HttpProxyController):
    storage: Storage

    def __init__(self):
        super().__init__("http://localhost:4999/", name="ui")
        self.router = self.create_router()
        self.storage = Storage()

    def create_router(self):
        router = Router(trim_last_slash=True)
        router.route("/api/transactions")(self.list_transactions)
        router.route("/api/transactions/{transaction}")(self.get_transaction)
        router.route("/api/blobs/{blob}")(self.get_blob)
        return router

    async def __call__(self, request: ASGIRequest, response: ASGIResponder, *, transaction_id=None):
        try:
            match = self.router(request.path, method=request.method)
            return await match.target(request, response, **(match.params or {}))
        except NotFoundError:
            return await super().__call__(request, response, transaction_id=transaction_id)

    async def list_transactions(self, request, response):
        transactions = []
        async for transaction in self.storage.find_transactions():
            transactions.append(transaction)
        return json(
            {"items": transactions, "total": len(transactions), "limit": 50, "offset": 0, "page": 1, "pages": 1}
        )

    async def get_transaction(self, request, response, transaction):
        return json(
            {
                "@type": "transaction",
                "@id": transaction,
            }
        )

    async def get_blob(self, request, response, blob):
        return json(
            {
                "@type": "blob",
                "@id": blob,
            }
        )
