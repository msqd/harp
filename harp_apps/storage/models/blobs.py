import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import yaml
from sqlalchemy import TIMESTAMP, LargeBinary, String, delete, func, select
from sqlalchemy.orm import aliased, mapped_column

from harp import get_logger
from harp.models import Blob as BlobModel

from .base import Base, Repository, with_session
from .messages import Message

logger = get_logger(__name__)
_YamlLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class Blob(Base):
    __tablename__ = "blobs"

    # Wide enough for every identifier this table holds, which is not one scheme: message blobs are
    # keyed by a sha1 hexdigest (40 characters) and HTTP cache entries by hishel, which uses sha256
    # (64). PostgreSQL and MySQL enforce the declared width, so sizing this to one of the two makes
    # the other fail its insert.
    id = mapped_column(String(64), primary_key=True, unique=True)
    data = mapped_column(LargeBinary())
    content_type = mapped_column(String(64))
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


#: How long a blob is protected from the orphan sweep after it was last written.
#:
#: A producer stores its blobs first, then the message referencing them, so for a
#: moment a freshly written blob is referenced by nothing. Writing content that is already stored
#: renews the protection, see `SqlBlobStorage.put`.
ORPHAN_GRACE = timedelta(minutes=10)

_SCAN_BATCH = 1000
_DELETE_CHUNK = 500


class BlobsRepository(Repository[Blob]):
    """An orphan is a blob no message references. Count, selection and deletion all read the same definition,
    :meth:`find_orphans`.

    The HTTP cache keeps nothing here: the ``cache/meta`` blobs of the cache of earlier versions, and the blobs they
    pointed at, are orphans like any other.
    """

    Type = Blob

    @asynccontextmanager
    async def _batch_session(self, session):
        """The caller's session when it brought one, else a fresh one that ends with the batch.

        A sweep reads in batches: on a store with a single connection (the default in-memory SQLite),
        holding one session for the whole pass would keep every request waiting.
        """
        if session is not None:
            yield session
            return
        async with self.session_factory() as own:
            yield own

    def _orphans_query(self, after: str, upto: str, older_than: datetime | None):
        """Ids in ``(after, upto]`` that no message references (hence no joined row counts)."""
        MH = aliased(Message, name="mh")
        MB = aliased(Message, name="mb")
        query = (
            select(Blob.id)
            .select_from(Blob)
            .outerjoin(MH, MH.headers == Blob.id)
            .outerjoin(MB, MB.body == Blob.id)
            .where(Blob.id > after, Blob.id <= upto)
            .group_by(Blob.id)
            .having(func.count(MH.id) + func.count(MB.id) == 0)
        )
        if older_than is not None:
            query = query.where(Blob.created_at < older_than)
        return query

    async def _candidates(self, session, older_than: datetime | None) -> list[str]:
        candidates: list[str] = []
        last_id = ""
        while True:
            async with self._batch_session(session) as batch:
                page = (
                    (await batch.execute(select(Blob.id).where(Blob.id > last_id).order_by(Blob.id).limit(_SCAN_BATCH)))
                    .scalars()
                    .all()
                )
                if not page:
                    return candidates
                query = self._orphans_query(last_id, page[-1], older_than)
                candidates.extend((await batch.execute(query)).scalars().all())
            await asyncio.sleep(0)
            if len(page) < _SCAN_BATCH:
                return candidates
            last_id = page[-1]

    async def find_orphans(self, /, *, session=None, older_than: datetime | None = None) -> list[str]:
        """Ids of the blobs referenced by nothing, optionally only those written before `older_than`.

        Scans in short batches, each in its own session unless the caller passes one.
        """
        return await self._candidates(session, older_than)

    async def count_orphans(self, /, *, session=None) -> int:
        return len(await self.find_orphans(session=session))

    async def delete_orphans(self, orphans: list[str], /, *, session=None, older_than: datetime | None = None) -> int:
        """Delete the given ids, as returned by `find_orphans`, one short transaction per chunk.

        `older_than` is applied again here: a blob written again since the ids were read is no
        longer eligible.
        """
        deleted = 0
        for i in range(0, len(orphans), _DELETE_CHUNK):
            query = delete(Blob).where(Blob.id.in_(orphans[i : i + _DELETE_CHUNK]))
            if older_than is not None:
                query = query.where(Blob.created_at < older_than)
            async with self._batch_session(session) as batch:
                result = await batch.execute(query)
                await batch.commit()
            deleted += result.rowcount or 0
            await asyncio.sleep(0)
        return deleted

    async def referenced_by_messages(self, blob_ids: list[str], /, *, session=None) -> set[str]:
        """The given ids that at least one message references, as headers or as body.

        Asks the messages table, not the blobs table: for blob backends that live elsewhere (Redis, memory) this
        table holds no blob. One short query per chunk, each in its own session unless the caller passes one.
        """
        referenced: set[str] = set()
        for i in range(0, len(blob_ids), _DELETE_CHUNK):
            chunk = blob_ids[i : i + _DELETE_CHUNK]
            async with self._batch_session(session) as batch:
                for column in (Message.headers, Message.body):
                    referenced.update(
                        (await batch.execute(select(column).where(column.in_(chunk)).distinct())).scalars()
                    )
            await asyncio.sleep(0)
        return referenced

    @with_session
    async def create(self, values: dict | BlobModel, /, *, session):
        if isinstance(values, BlobModel):
            values = dict(
                id=values.id,
                data=values.data,
                content_type=values.content_type,
            )
        return await super().create(values, session=session)
