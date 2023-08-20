from blacksheep import json
from blacksheep.server.controllers import Controller, get

from harp.models.transaction import Transaction
from harp.services.storage import Storage


class ApiController(Controller):
    @get("/")
    async def get(self, storage: Storage):
        return json({"items": [transaction.asdict() for transaction in reversed(storage.select(Transaction))]})
