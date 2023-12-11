import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from config.common import Configuration
from http_router import NotFoundError, Router

from harp import ROOT_DIR, get_logger
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.models.transactions import Transaction
from harp.core.views.json import json
from harp.protocols.storage import IStorage

STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "../frontend/dist")),
    "/opt/harp/public",
]

logger = get_logger(__name__)


class DashboardController(HttpProxyController):
    name = "ui"
    storage: IStorage
    proxy_settings: Configuration

    middleware = None

    def __init__(self, storage: IStorage, proxy_settings: Configuration):
        super().__init__("http://localhost:4999/")

        self.router = self.create_router()
        self.storage = storage
        self.proxy_settings = proxy_settings

        # todo use delegation instead of inheritance, this is not clean.
        for _path in STATIC_BUILD_PATHS:
            logger.info("Checking for static files in %s", _path)
            if os.path.exists(_path):
                logger.info("Serving static files from %s", _path)
                self.middleware = ASGIMiddlewareStaticFile(None, "", [_path])
                break

    def create_router(self):
        router = Router(trim_last_slash=True)
        router.route("/api/transactions")(self.list_transactions)
        router.route("/api/transactions/{transaction}")(self.get_transaction)
        router.route("/api/blobs/{blob}")(self.get_blob)
        router.route("/api/settings")(self.get_settings)
        return router

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        if self.middleware and not request.path.startswith("/api/"):
            try:
                return await self.middleware(
                    {
                        "type": request._scope["type"],
                        "path": (request._scope["path"] + "index.html")
                        if request._scope["path"].endswith("/")
                        else request._scope["path"],
                        "method": request._scope["method"],
                    },
                    request._receive,
                    response._send,
                )
            finally:
                response.started = True

        try:
            match = self.router(request.path, method=request.method)
            return await match.target(request, response, **(match.params or {}))
        except NotFoundError:
            return await super().__call__(request, response, transaction_id=transaction_id)

    async def list_transactions(self, request, response):
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

    async def get_transaction(self, request, response, transaction):
        return json(
            {
                "@type": "transaction",
                "@id": transaction,
            }
        )

    async def get_blob(self, request, response, blob):
        blob = await self.storage.get_blob(blob)

        if not blob:
            await response.start(status=404, headers={"content-type": "text/plain"})
            await response.body(b"Blob not found.")
            return

        await response.start(status=200, headers={"content-type": "application/octet-stream"})
        await response.body(blob.data)

    async def get_settings(self, request, response):
        return json(self.proxy_settings.values)
