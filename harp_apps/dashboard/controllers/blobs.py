from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpResponse
from harp.typing.storage import Storage


@RouterPrefix("/api/blobs")
class BlobsController(RoutingController):
    def __init__(self, *, storage: Storage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/{id}")
    async def get(self, id):
        blob = await self.storage.get_blob(id)
        if not blob:
            return HttpResponse(b"Blob not found.", status=404, content_type="text/plain")

        content_type = blob.content_type or "application/octet-stream"

        if content_type == "application/json":
            return HttpResponse(blob.prettify(), content_type=content_type)
        return HttpResponse(blob.data, content_type=content_type)
