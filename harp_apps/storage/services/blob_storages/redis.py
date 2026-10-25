import time
from collections.abc import AsyncIterator, Iterable
from datetime import datetime
from typing import override

from redis.asyncio import Redis

from harp.models import Blob
from harp_apps.storage.models.blobs import ORPHAN_GRACE
from harp_apps.storage.types import IBlobStorage

#: Every blob lives at ``<prefix><blob id>``: the Redis database may be shared with other applications, whose keys HARP
#: never lists or sweeps. Blobs stored before the prefix existed sit under their bare id: they are still read and
#: deleted by id, but never listed.
BLOB_PREFIX = "harp:blob:"

#: Marks a blob as recently written: key ``<prefix><blob id>``, holding the write time, living `ORPHAN_GRACE`.
#: Redis blobs have no ``created_at``; the marker is what keeps the janitor from deleting content whose message is
#: not committed yet, as ``blobs.created_at`` does for SQL.
WRITE_MARKER_PREFIX = "harp:blob-written:"

SCAN_BATCH_SIZE = 500

# Deletes the blobs (KEYS, prefixed by ARGV[3]) whose write marker is older than ARGV[1], or missing. Atomic: a
# producer storing the same content again cannot slip in between the check and the deletion.
_DELETE_STALE = """
local deleted = 0
for _, key in ipairs(KEYS) do
    local written = redis.call('GET', ARGV[2] .. string.sub(key, #ARGV[3] + 1))
    if not written or tonumber(written) < tonumber(ARGV[1]) then
        deleted = deleted + redis.call('DEL', key)
    end
end
return deleted
"""

# Deletes the blobs (KEYS) still holding exactly the given value (ARGV, same order).
_DELETE_IF_UNCHANGED = """
local deleted = 0
for i, id in ipairs(KEYS) do
    if redis.call('GET', id) == ARGV[i] then
        deleted = deleted + redis.call('DEL', id)
    end
end
return deleted
"""


def _encode(blob: Blob) -> bytes:
    return ((blob.content_type or "") + "\n").encode() + blob.data


class RedisBlobStorage(IBlobStorage):
    type = "redis"

    def __init__(self, client: Redis):
        self.client = client

    @override
    async def get(self, blob_id):
        data = await self.client.get(BLOB_PREFIX + blob_id)
        if data is None:
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
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.set(BLOB_PREFIX + blob.id, _encode(blob))
            pipe.set(WRITE_MARKER_PREFIX + blob.id, time.time(), ex=int(ORPHAN_GRACE.total_seconds()))
            await pipe.execute()
        return blob

    force_put = put

    @override
    async def delete(self, blob_id):
        await self.client.delete(BLOB_PREFIX + blob_id, blob_id)

    @override
    async def exists(self, blob_id: str) -> bool:
        return bool(await self.client.exists(BLOB_PREFIX + blob_id, blob_id))

    async def iter_blob_ids(self) -> AsyncIterator[str]:
        """Every blob id stored under the HARP prefix."""
        async for key in self.client.scan_iter(match=BLOB_PREFIX + "*", count=SCAN_BATCH_SIZE):
            key = key.decode() if isinstance(key, bytes) else key
            yield key.removeprefix(BLOB_PREFIX)

    async def iter_blobs(self, content_type: str) -> AsyncIterator[Blob]:
        """Every stored blob of this content type.

        Only the first bytes of each value are read to tell the type, so the bodies of other blobs stay in Redis.
        """
        header = (content_type + "\n").encode()
        batch: list[str] = []
        async for blob_id in self.iter_blob_ids():
            batch.append(blob_id)
            if len(batch) >= SCAN_BATCH_SIZE:
                async for blob in self._matching(batch, header):
                    yield blob
                batch = []
        async for blob in self._matching(batch, header):
            yield blob

    async def _matching(self, blob_ids: list[str], header: bytes) -> AsyncIterator[Blob]:
        if not blob_ids:
            return
        async with self.client.pipeline(transaction=False) as pipe:
            for blob_id in blob_ids:
                pipe.getrange(BLOB_PREFIX + blob_id, 0, len(header) - 1)
            starts = await pipe.execute()
        for blob_id, start in zip(blob_ids, starts):
            if start == header:
                blob = await self.get(blob_id)
                if blob is not None:
                    yield blob

    async def delete_blobs(self, blobs: Iterable[Blob]) -> None:
        """Delete each blob, unless it was stored again with other data since it was read."""
        blobs = list(blobs)
        if blobs:
            await self.client.eval(
                _DELETE_IF_UNCHANGED, len(blobs), *(BLOB_PREFIX + b.id for b in blobs), *(_encode(b) for b in blobs)
            )

    async def delete_stale(self, blob_ids: Iterable[str], /, *, older_than: datetime) -> int:
        """Delete the given blobs, except those written after `older_than`. Returns how many were deleted."""
        blob_ids = list(blob_ids)
        if not blob_ids:
            return 0
        return await self.client.eval(
            _DELETE_STALE,
            len(blob_ids),
            *(BLOB_PREFIX + i for i in blob_ids),
            older_than.timestamp(),
            WRITE_MARKER_PREFIX,
            BLOB_PREFIX,
        )
