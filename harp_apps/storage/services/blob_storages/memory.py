from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime

from harp.models import Blob
from harp_apps.storage.types import IBlobStorage


class MemoryBlobStorage(IBlobStorage):
    type = "memory"

    def __init__(self):
        super().__init__()
        self._blobs = {}
        self._written: dict[str, datetime] = {}

    async def get(self, blob_id: str):
        return self._blobs.get(blob_id, None)

    async def put(self, blob: Blob) -> Blob:
        self._blobs[blob.id] = blob
        self._written[blob.id] = datetime.now(UTC)
        return blob

    force_put = put

    async def delete(self, blob_id: str):
        self._blobs.pop(blob_id, None)
        self._written.pop(blob_id, None)

    async def delete_blobs(self, blobs: Iterable[Blob]) -> None:
        """Delete each blob, unless it was stored again with other data since it was read."""
        for blob in blobs:
            stored = self._blobs.get(blob.id)
            if stored is not None and stored.data == blob.data:
                await self.delete(blob.id)

    async def exists(self, blob_id: str) -> bool:
        return blob_id in self._blobs

    async def iter_blobs(self, content_type: str) -> AsyncIterator[Blob]:
        for blob in list(self._blobs.values()):
            if blob.content_type == content_type:
                yield blob

    async def iter_blob_ids(self) -> AsyncIterator[str]:
        for blob_id in list(self._blobs):
            yield blob_id

    async def delete_stale(self, blob_ids: Iterable[str], /, *, older_than: datetime) -> int:
        """Delete the given blobs, except those written after `older_than`. Returns how many were deleted."""
        deleted = 0
        for blob_id in blob_ids:
            if blob_id in self._blobs and self._written[blob_id] < older_than:
                await self.delete(blob_id)
                deleted += 1
        return deleted
