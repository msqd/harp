from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpResponse
from harp_apps.storage.types import IBlobStorage


@RouterPrefix("/api/blobs")
class BlobsController(RoutingController):
    def __init__(self, *, storage: IBlobStorage, handle_errors=True, router=None):
        self.storage = storage
        super().__init__(handle_errors=handle_errors, router=router)

    @GetHandler("/{id}")
    async def get(self, id):
        blob = await self.storage.get(id)
        if not blob:
            return HttpResponse(b"Blob not found.", status=404, content_type="text/plain")

        content_type = blob.content_type or "application/octet-stream"

        try:
            data = blob.prettify()
        except (ValueError, NotImplementedError):
            data = blob.data

        return HttpResponse(data, content_type=content_type)
