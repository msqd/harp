from harp.models import Blob
from harp_apps.storage.types import IBlobStorage


class NullBlobStorage(IBlobStorage):
    type = "null"

    async def get(self, blob_id: str):
        return None

    async def put(self, blob: Blob) -> Blob:
        return blob

    async def delete(self, blob_id: str):
        pass

    async def exists(self, blob_id: str) -> bool:
        return False
