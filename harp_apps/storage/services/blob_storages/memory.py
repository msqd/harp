from collections.abc import AsyncIterator

from harp.models import Blob
from harp_apps.storage.types import IBlobStorage


class MemoryBlobStorage(IBlobStorage):
    type = "memory"

    def __init__(self):
        super().__init__()
        self._blobs = {}

    async def get(self, blob_id: str):
        return self._blobs.get(blob_id, None)

    async def put(self, blob: Blob) -> Blob:
        self._blobs[blob.id] = blob
        return blob

    force_put = put

    async def delete(self, blob_id: str):
        del self._blobs[blob_id]

    async def exists(self, blob_id: str) -> bool:
        return False

    async def iter_blobs(self, content_type: str) -> AsyncIterator[Blob]:
        for blob in list(self._blobs.values()):
            if blob.content_type == content_type:
                yield blob
