import asyncio
from datetime import datetime, timedelta

import yaml
from sqlalchemy import TIMESTAMP, LargeBinary, String, delete, func, or_, select
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


CACHE_META_CONTENT_TYPE = "cache/meta"

#: How long a blob is protected from the orphan sweep after it was last written.
#:
#: A producer stores its blobs first, then the message (or cache entry) referencing them, so for a
#: moment a freshly written blob is referenced by nothing. Writing content that is already stored
#: renews the protection, see `SqlBlobStorage.put`.
ORPHAN_GRACE = timedelta(minutes=10)

_CACHE_META_BATCH = 200
_DELETE_CHUNK = 500


def cache_meta_references(data: bytes) -> set[str]:
    """The blob ids a ``cache/meta`` blob points at: request headers, response headers and body.

    A blob that cannot be read references nothing; its entry is already unusable.
    """
    try:
        meta = yaml.load(data, Loader=_YamlLoader)
        return {
            meta["request"]["headers"],
            meta["response"]["headers"],
            meta["response"]["body"],
        }
    except (yaml.YAMLError, KeyError, TypeError):
        logger.warning("Unreadable cache/meta blob, its references are ignored.")
        return set()


class BlobsRepository(Repository[Blob]):
    """An orphan is a blob nothing references: no message, and no ``cache/meta`` entry.

    ``cache/meta`` blobs themselves are never orphans, the cache's TTL sweep reclaims them. Count,
    selection and deletion all read the same definition, :meth:`find_orphans`.
    """

    Type = Blob

    def _orphans_subquery(self):
        """Blobs paired with the number of messages referencing them, so zero means unreferenced."""
        MH = aliased(Message, name="mh")
        MB = aliased(Message, name="mb")
        return (
            select(Blob.id, func.count(MH.id) + func.count(MB.id))
            .select_from(Blob)
            .outerjoin(MH, MH.headers == Blob.id)
            .outerjoin(MB, MB.body == Blob.id)
            .where(or_(Blob.content_type.is_(None), Blob.content_type != CACHE_META_CONTENT_TYPE))
            .group_by(Blob.id)
            .subquery()
        )

    @with_session
    async def _cache_references(self, /, *, session) -> set[str]:
        references: set[str] = set()
        result = await session.stream_scalars(
            select(Blob.data)
            .where(Blob.content_type == CACHE_META_CONTENT_TYPE)
            .execution_options(yield_per=_CACHE_META_BATCH)
        )
        count = 0
        async for data in result:
            references |= cache_meta_references(data)
            count += 1
            if count % _CACHE_META_BATCH == 0:
                await asyncio.sleep(0)  # a large cache must not hold the event loop for the whole pass
        return references

    @with_session
    async def find_orphans(self, /, *, session, older_than: datetime | None = None) -> list[str]:
        """Ids of the blobs referenced by nothing, optionally only those written before `older_than`."""
        subquery = self._orphans_subquery()
        query = select(subquery.c.id).where(subquery.c[1] == 0)
        if older_than is not None:
            query = query.join(Blob, Blob.id == subquery.c.id).where(Blob.created_at < older_than)
        candidates = (await session.execute(query)).scalars().all()
        referenced = await self._cache_references(session=session)
        return [blob_id for blob_id in candidates if blob_id not in referenced]

    @with_session
    async def count_orphans(self, /, *, session) -> int:
        return len(await self.find_orphans(session=session))

    @with_session
    async def delete_orphans(self, orphans: list[str], /, *, session, older_than: datetime | None = None) -> int:
        """Delete the given ids, as returned by `find_orphans`, in chunks the database accepts.

        `older_than` is applied again here: a blob written again since the ids were read is no
        longer eligible.
        """
        deleted = 0
        for i in range(0, len(orphans), _DELETE_CHUNK):
            query = delete(Blob).where(Blob.id.in_(orphans[i : i + _DELETE_CHUNK]))
            if older_than is not None:
                query = query.where(Blob.created_at < older_than)
            result = await session.execute(query)
            deleted += result.rowcount or 0
        await session.commit()
        return deleted

    @with_session
    async def create(self, values: dict | BlobModel, /, *, session):
        if isinstance(values, BlobModel):
            values = dict(
                id=values.id,
                data=values.data,
                content_type=values.content_type,
            )
        return await super().create(values, session=session)
