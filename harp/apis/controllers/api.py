from blacksheep import json, not_found
from blacksheep.server.controllers import Controller, get

from harp.models.request import DeprecatedOldTransactionRequest
from harp.models.response import DeprecatedOldTransactionResponse
from harp.services.storage import Storage


class ApiController(Controller):
    @get("/api/requests/{id}")
    async def get_request(self, storage: Storage, id: str):
        try:
            entity: DeprecatedOldTransactionRequest = storage.find(DeprecatedOldTransactionRequest, id)
            return json(entity.asdict(with_details=True))
        except KeyError:
            return not_found()

    @get("/api/responses/{id}")
    async def get_response(self, storage: Storage, id: str):
        try:
            entity: DeprecatedOldTransactionResponse = storage.find(DeprecatedOldTransactionResponse, id)
            return json(entity.asdict(with_details=True))
        except KeyError:
            return not_found()
