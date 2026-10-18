from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import override

from sqlalchemy import and_, delete, or_, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from harp import get_logger
from harp.models import Blob
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.models.blobs import ORPHAN_GRACE
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.upsert import insert_ignoring_duplicates

logger = get_logger(__name__)

ITER_BATCH_SIZE = 200
DELETE_BATCH_SIZE = 200


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
            # One conditional statement: reading `created_at` first would leave the janitor a window to delete
            # the blob before it is renewed.
            renewed = await conn.execute(
                update(SqlBlob)
                .where(SqlBlob.id == blob.id, SqlBlob.created_at < datetime.now(UTC) - ORPHAN_GRACE / 2)
                .values(created_at=func.now())
            )
            await conn.commit()
            # the check shares `conn`: a second connection would deadlock a pool of one
            if (
                renewed.rowcount == 0
                and not (await conn.execute(select(SqlBlob.id).where(SqlBlob.id == blob.id))).first()
            ):
                try:
                    await conn.execute(
                        insert(SqlBlob).values(id=blob.id, data=blob.data, content_type=blob.content_type),
                    )
                    await conn.commit()
                except IntegrityError:
                    pass  # already there? that's fine!
        return blob

    async def put_in(self, conn: AsyncConnection, blobs: Sequence[Blob]) -> None:
        """
        Store blobs on ``conn``, inside the caller's database transaction: two statements for any number of blobs.

        Same guarantee as :meth:`put` (see ``ORPHAN_GRACE``), with the renewal committing together with the message that
        references the blob. Blobs already there are left alone, or renewed once old.
        """
        if not blobs:
            return
        table = SqlBlob.__table__
        await conn.execute(
            update(table)
            .where(
                table.c.id.in_([blob.id for blob in blobs]), table.c.created_at < datetime.now(UTC) - ORPHAN_GRACE / 2
            )
            .values(created_at=func.now())
        )
        await conn.execute(
            insert_ignoring_duplicates(conn.dialect.name, table),
            [{"id": blob.id, "data": blob.data, "content_type": blob.content_type} for blob in blobs],
        )

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

    async def delete_blobs(self, blobs: Sequence[Blob]) -> None:
        """
        Delete blobs in chunks, one statement and one transaction per chunk.

        A blob stored again with other data since it was read is left alone.
        """
        for start in range(0, len(blobs), DELETE_BATCH_SIZE):
            chunk = blobs[start : start + DELETE_BATCH_SIZE]
            async with self.engine.connect() as conn:
                await conn.execute(
                    delete(SqlBlob).where(or_(*(and_(SqlBlob.id == b.id, SqlBlob.data == b.data) for b in chunk)))
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
        """Every stored blob of this content type.

        Read in short batches, each on its own connection, so no read transaction stays open while the
        caller works on a row: on SQLite a long streamed read would keep writers waiting.
        """
        last_id = ""
        while True:
            async with self.engine.connect() as conn:
                rows = (
                    await conn.execute(
                        select(SqlBlob)
                        .where(SqlBlob.content_type == content_type, SqlBlob.id > last_id)
                        .order_by(SqlBlob.id)
                        .limit(ITER_BATCH_SIZE)
                    )
                ).fetchall()
            for row in rows:
                yield Blob(id=row.id, data=row.data, content_type=row.content_type)
            if len(rows) < ITER_BATCH_SIZE:
                return
            last_id = rows[-1].id
