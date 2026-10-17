from collections.abc import AsyncIterator, Iterable

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
        self._blobs.pop(blob_id, None)

    async def delete_blobs(self, blobs: Iterable[Blob]) -> None:
        """Delete each blob, unless it was stored again with other data since it was read."""
        for blob in blobs:
            stored = self._blobs.get(blob.id)
            if stored is not None and stored.data == blob.data:
                del self._blobs[blob.id]

    async def exists(self, blob_id: str) -> bool:
        return False

    async def iter_blobs(self, content_type: str) -> AsyncIterator[Blob]:
        for blob in list(self._blobs.values()):
            if blob.content_type == content_type:
                yield blob
