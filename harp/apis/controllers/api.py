from blacksheep import json, not_found
from blacksheep.server.controllers import Controller, get

from harp.models.request import TransactionRequest
from harp.models.response import TransactionResponse
from harp.models.transaction import Transaction
from harp.services.storage import Storage


class ApiController(Controller):
    @get("/api/transactions")
    async def list_transactions(self, storage: Storage):
        return json({"items": [transaction.asdict() for transaction in storage.select(Transaction)]})

    @get("/api/requests/{id}")
    async def get_request(self, storage: Storage, id: str):
        try:
            entity: TransactionRequest = storage.find(TransactionRequest, id)
            return json(entity.asdict(with_details=True))
        except KeyError:
            return not_found()

    @get("/api/responses/{id}")
    async def get_response(self, storage: Storage, id: str):
        try:
            entity: TransactionResponse = storage.find(TransactionResponse, id)
            return json(entity.asdict(with_details=True))
        except KeyError:
            return not_found()
