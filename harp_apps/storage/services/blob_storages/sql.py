from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import override

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from harp import get_logger
from harp.models import Blob
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.models.blobs import ORPHAN_GRACE
from harp_apps.storage.types import IBlobStorage

logger = get_logger(__name__)


def _is_older_than(moment: datetime, age: timedelta) -> bool:
    if moment.tzinfo is None:  # sqlite hands back naive UTC
        moment = moment.replace(tzinfo=UTC)
    return datetime.now(UTC) - moment > age


class SqlBlobStorage(IBlobStorage):
    type = "sql"

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

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
        Store a blob in the database, unless it is already there.

        Always asks the database: another process (the janitor, another instance) may have deleted
        the row since this one last wrote it, and a local memory of "stored" cannot know.

        Content that is already stored is written again in the one way that matters: its
        `created_at` is renewed once it gets old, so the orphan sweep leaves it alone while the
        message that is about to reference it commits. See `ORPHAN_GRACE`.

        :param blob: content-addressed blob (sha1 for message blobs, sha256 for cache entries)
        """
        async with self.engine.connect() as conn:
            created_at = (
                await conn.execute(select(SqlBlob.created_at).where(SqlBlob.id == blob.id))
            ).scalar_one_or_none()
            if created_at is None:
                try:
                    await conn.execute(
                        insert(SqlBlob).values(id=blob.id, data=blob.data, content_type=blob.content_type),
                    )
                    await conn.commit()
                except IntegrityError:
                    pass  # already there? that's fine!
            elif _is_older_than(created_at, ORPHAN_GRACE / 2):
                await conn.execute(update(SqlBlob).where(SqlBlob.id == blob.id).values(created_at=func.now()))
                await conn.commit()
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
        async with self.engine.connect() as conn:
            await conn.execute(
                delete(SqlBlob).where(SqlBlob.id == blob_id),
            )
            await conn.commit()

    @override
    async def exists(self, blob_id: str) -> bool:
        """
        Check if a blob exists in the database.

        :param blob_id: content hash identifying the blob (sha1 for message blobs, sha256 for cache entries)
        :return: True if the blob exists, False otherwise
        """
        async with self.engine.connect() as conn:
            return bool(
                (
                    await conn.execute(
                        select(
                            select(SqlBlob.id).where(SqlBlob.id == blob_id).exists(),
                        ),
                    )
                ).scalar_one()
            )

    async def iter_blobs(self, content_type: str) -> AsyncIterator[Blob]:
        """Every stored blob of this content type."""
        async with self.engine.connect() as conn:
            result = await conn.stream(
                select(SqlBlob).where(SqlBlob.content_type == content_type).execution_options(yield_per=200)
            )
            async for row in result:
                yield Blob(id=row.id, data=row.data, content_type=row.content_type)
