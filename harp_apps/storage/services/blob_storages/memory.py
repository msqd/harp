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

    async def delete(self, blob_id: str):
        del self._blobs[blob_id]

    async def exists(self, blob_id: str) -> bool:
        return False
