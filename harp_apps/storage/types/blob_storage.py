from typing import Protocol

from harp.models import Blob


class IBlobStorage(Protocol):
    type: str

    async def get(self, blob_id: str): ...

    async def put(self, blob: Blob) -> Blob: ...

    async def force_put(self, blob: Blob) -> Blob: ...

    async def delete(self, blob_id: str): ...

    async def exists(self, blob_id: str) -> bool: ...

    # Optional capability: `iter_blobs(content_type)` yields every stored blob of that content type
    # (async iterator). Backends that cannot enumerate, such as Redis, do not define it.
    # Optional capability: `delete_blobs(blobs)` deletes each given blob, in batches where the backend can,
    # unless it was stored again with other data since it was read. Absent keys are ignored.
