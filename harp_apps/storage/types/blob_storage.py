from collections.abc import Iterable
from typing import Protocol

from harp.models import Blob


class IBlobStorage(Protocol):
    type: str

    async def get(self, blob_id: str): ...

    async def put(self, blob: Blob) -> Blob: ...

    async def force_put(self, blob: Blob) -> Blob: ...

    async def delete(self, blob_id: str): ...

    async def exists(self, blob_id: str) -> bool: ...

    def forget(self, blob_ids: Iterable[str]) -> None:
        """Discard anything cached about these blobs, which have been removed by other means.

        A backend that caches "this blob exists" has to be told when something deletes rows without
        going through `delete`, or it will keep answering from a belief that is no longer true.
        Backends holding no such cache may ignore this.
        """
