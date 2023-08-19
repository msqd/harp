from pprint import pprint

import rodi
from blacksheep import Application, json
from blacksheep.server.controllers import Controller, get

from harp.models.transaction import Transaction
from harp.services.storage import Storage


class ApiController(Controller):
    @get("/")
    async def get(self, storage: Storage):
        return json({"items": [transaction.asdict() for transaction in reversed(storage.select(Transaction))]})


class ManagementApplication(Application):
    def __init__(self, *, container: rodi.Container):
        super().__init__(services=container)

        self.use_cors(
            allow_methods="*",
            allow_origins="*",
            allow_headers="* Authorization",
            max_age=300,
        )

        @self.after_start
        async def after_start_print_routes(application: Application) -> None:
            pprint(dict(application.router.routes))
