from harp.controllers import GetHandler, RouterPrefix, RoutingController
from harp.http import HttpResponse
from harp_apps.storage.types import IBlobStorage

#: Blobs are captured traffic, hence untrusted. The dashboard reads them with fetch(), which needs the recorded
#: content type, but a browser opening a blob URL directly must never render it as a document in the dashboard
#: origin: download it instead, never sniff its type, and if rendered anyway, sandbox it with no script nor resource.
INERT_BLOB_HEADERS = {
    "Content-Disposition": "attachment",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "sandbox; default-src 'none'",
}


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

        return HttpResponse(data, content_type=content_type, headers=INERT_BLOB_HEADERS)
