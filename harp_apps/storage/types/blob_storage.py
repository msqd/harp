from typing import Protocol

from harp.models import Blob


class IBlobStorage(Protocol):
    type: str

    async def get(self, blob_id: str): ...

    async def put(self, blob: Blob) -> Blob: ...

    async def delete(self, blob_id: str): ...

    async def exists(self, blob_id: str) -> bool: ...
