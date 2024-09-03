from typing import override

from redis.asyncio import Redis

from harp.models import Blob
from harp_apps.storage.types import IBlobStorage


class RedisBlobStorage(IBlobStorage):
    type = "redis"

    def __init__(self, client: Redis):
        self.client = client

    @override
    async def get(self, blob_id):
        data = await self.client.get(blob_id)
        if data is not None:
            content_type, body = data.split(b"\n", 1)
            return Blob(
                id=blob_id,
                data=body,
                content_type=content_type.decode() if content_type else None,
            )

    @override
    async def put(self, blob: Blob) -> Blob:
        await self.client.set(blob.id, ((blob.content_type or "") + "\n").encode() + blob.data)
        return blob

    @override
    async def delete(self, blob_id):
        await self.client.delete(blob_id)

    @override
    async def exists(self, blob_id: str) -> bool:
        return await self.client.exists(blob_id)
