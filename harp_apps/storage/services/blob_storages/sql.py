import asyncio
from contextlib import asynccontextmanager
from typing import override

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from harp.models import Blob
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.types import IBlobStorage


class SqlBlobStorage(IBlobStorage):
    type = "sql"

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._write_lock = asyncio.Lock()

    @asynccontextmanager
    async def begin(self):
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    @override
    async def get(self, blob_id):
        """
        Retrieve a blob from the database, using its hash.
        Returns None if not found.

        :param blob_id: sha1 hash of the blob
        :return: Blob or None
        """
        async with self.begin() as session:
            row = (
                await session.execute(
                    select(SqlBlob).where(SqlBlob.id == blob_id),
                )
            ).fetchone()

        if row:
            return Blob(id=blob_id, data=row[0].data, content_type=row[0].content_type)

    @override
    async def put(self, blob: Blob) -> Blob:
        """
        Store a blob in the database.

        :param blob_id: sha1 hash of the blob
        :param data: blob data
        """
        async with self._write_lock:
            async with self.begin() as session:
                if not (
                    await session.execute(select(select(SqlBlob.id).where(SqlBlob.id == blob.id).exists()))
                ).scalar_one():
                    session.add(
                        SqlBlob(
                            id=blob.id,
                            content_type=blob.content_type,
                            data=blob.data,
                        )
                    )
        return blob

    @override
    async def delete(self, blob_id):
        """
        Delete a blob from the database.

        :param blob_id: sha1 hash of the blob
        """
        async with self.begin() as session:
            await session.execute(
                delete(SqlBlob).where(SqlBlob.id == blob_id),
            )

    @override
    async def exists(self, blob_id: str) -> bool:
        """
        Check if a blob exists in the database.

        :param blob_id: sha1 hash of the blob
        :return: True if the blob exists, False otherwise
        """
        async with self.begin() as session:
            row = (
                await session.execute(
                    select(SqlBlob).where(SqlBlob.id == blob_id),
                )
            ).fetchone()

        return bool(row)
