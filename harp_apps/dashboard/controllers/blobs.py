from harp.core.asgi import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.typing.storage import Storage


class BlobsController(RoutingController):
    prefix = "/api/blobs"

    def __init__(self, *, storage: Storage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    def configure(self):
        self.router.route(self.prefix + "/{id}")(self.get)

    async def get(self, request: ASGIRequest, response: ASGIResponse, id):
        blob = await self.storage.get_blob(id)

        if not blob:
            response.headers["content-type"] = "text/plain"
            await response.start(status=404)
            await response.body(b"Blob not found.")
            return

        response.headers["content-type"] = blob.content_type or "application/octet-stream"
        await response.start(status=200)

        if blob.content_type == "application/json":
            await response.body(blob.prettify())
        else:
            await response.body(blob.data)
