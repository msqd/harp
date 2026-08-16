from collections import OrderedDict
from collections.abc import Iterable
from typing import override

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from harp import get_logger
from harp.models import Blob
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.types import IBlobStorage

logger = get_logger(__name__)


class LRUSet:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = OrderedDict()

    def add(self, item):
        if item in self.items:
            # Move to the end to mark as recently used
            self.items.move_to_end(item)
        else:
            self.items[item] = True
            if len(self.items) > self.capacity:
                # Remove the least recently used item
                self.items.popitem(last=False)

    def remove(self, item):
        if item in self.items:
            del self.items[item]

    def exists(self, item):
        return item in self.items

    def get_lru(self):
        if self.items:
            return next(iter(self.items))
        return None

    def __repr__(self):
        return f"LRUSet({set(self.items.keys())})"


class SqlBlobStorage(IBlobStorage):
    type = "sql"

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.seen = LRUSet(1000)

    @override
    async def get(self, blob_id):
        """
        Retrieve a blob from the database, using its hash.
        Returns None if not found.

        :param blob_id: content hash identifying the blob (sha1 for message blobs, sha256 for cache entries)
        :return: Blob or None
        """
        async with self.engine.connect() as conn:
            result = await conn.execute(
                select(SqlBlob).where(SqlBlob.id == blob_id),
            )
            row = result.fetchone()
        if row:
            return Blob(id=blob_id, data=row.data, content_type=row.content_type)

    @override
    async def put(self, blob: Blob) -> Blob:
        """
        Store a blob in the database.

        :param blob_id: content hash identifying the blob (sha1 for message blobs, sha256 for cache entries)
        :param data: blob data
        """
        if self.seen.exists(blob.id):
            return blob

        async with self.engine.connect() as conn:
            if not (
                await conn.execute(
                    select(
                        select(SqlBlob.id).where(SqlBlob.id == blob.id).exists(),
                    ),
                )
            ).scalar_one():
                try:
                    await conn.execute(
                        insert(SqlBlob).values(id=blob.id, data=blob.data, content_type=blob.content_type),
                    )
                    await conn.commit()
                except IntegrityError:
                    pass  # already there? that's fine!
        # the blob is now known to be stored: remember it so later puts skip the existence query.
        # A cache populated from what you did, rather than from what the database confirmed, is only
        # valid while you are the only writer. Anything else deleting rows (the janitor sweep does,
        # in bulk) has to call `forget()`, or this entry outlives the row it stands for and both
        # `put()` and `exists()` go on answering from it.
        self.seen.add(blob.id)
        return blob

    @override
    async def force_put(self, blob: Blob) -> Blob:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(
                    insert(SqlBlob).values(id=blob.id, data=blob.data, content_type=blob.content_type),
                )
                await conn.commit()
        except IntegrityError:
            async with self.engine.connect() as conn:
                await conn.execute(
                    update(SqlBlob).where(SqlBlob.id == blob.id).values(data=blob.data, content_type=blob.content_type),
                )
                await conn.commit()
        return blob

    @override
    async def delete(self, blob_id):
        """
        Delete a blob from the database.

        :param blob_id: content hash identifying the blob (sha1 for message blobs, sha256 for cache entries)
        """
        self.seen.remove(blob_id)
        async with self.engine.connect() as conn:
            await conn.execute(
                delete(SqlBlob).where(SqlBlob.id == blob_id),
            )
            await conn.commit()

    @override
    def forget(self, blob_ids: Iterable[str]) -> None:
        """Drop the `seen` entries for blobs deleted without going through `delete`.

        Both `put()` and `exists()` answer from `seen`, so both are wrong about a swept blob until
        this is called.
        """
        for blob_id in blob_ids:
            self.seen.remove(blob_id)

    @override
    async def exists(self, blob_id: str) -> bool:
        """
        Check if a blob exists in the database.

        :param blob_id: content hash identifying the blob (sha1 for message blobs, sha256 for cache entries)
        :return: True if the blob exists, False otherwise
        """
        if self.seen.exists(blob_id):
            return True

        async with self.engine.connect() as conn:
            found = bool(
                (
                    await conn.execute(
                        select(
                            select(SqlBlob.id).where(SqlBlob.id == blob_id).exists(),
                        ),
                    )
                ).scalar_one()
            )
        if found:
            # remember it so later exists()/put() calls skip the existence query.
            self.seen.add(blob_id)
        return found
