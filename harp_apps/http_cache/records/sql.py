import asyncio
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Optional, TypeVar

from sqlalchemy import Row, delete, exists, select, tuple_
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from harp import get_logger
from harp_apps.http_cache.models import CacheBody, CacheResource, CacheStats, CacheVariant

from .base import CacheRecords, EndpointStats, StoredVariant, VariantRecord, endpoint_of

logger = get_logger(__name__)

T = TypeVar("T")

#: How many times a write is attempted when it meets a concurrent one: two writers of a variant, or a delete of the
#: last reference to a body that a writer is taking.
ATTEMPTS = 5

#: SQLSTATE of a transaction PostgreSQL rolled back to break a deadlock, or to serialize it.
_RETRYABLE_SQLSTATES = ("40P01", "40001")

_FIELDS = tuple(column.name for column in CacheVariant.__table__.columns)


def _record(row: Row) -> VariantRecord:
    return VariantRecord(**{name: row._mapping[name] for name in _FIELDS})


class SqlCacheRecords(CacheRecords):
    """The records in the storage database, tables ``http_cache_*`` (ADR-0014): shared by every instance of HARP."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    @property
    def _dialect(self):
        return {"postgresql": postgresql, "sqlite": sqlite}[self.engine.dialect.name]

    async def get_variants(self, key: str) -> list[StoredVariant]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(CacheVariant.__table__, CacheBody.data)
                    .join(CacheBody, CacheBody.digest == CacheVariant.body_digest)
                    .where(CacheVariant.key == key)
                    .order_by(CacheVariant.stored_at, CacheVariant.variant)
                )
            ).all()
        return [StoredVariant(_record(row), bytes(row.data)) for row in rows]

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        async with self.engine.connect() as conn:
            row = (await conn.execute(select(CacheVariant.__table__).where(CacheVariant.entry_id == entry_id))).first()
        return _record(row) if row else None

    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> None:
        await self._write(lambda conn: self._put(conn, record, body, keep, replaces))

    async def _put(
        self, conn: AsyncConnection, record: VariantRecord, body: bytes, keep: int, replaces: Optional[uuid.UUID]
    ) -> None:
        insert = self._dialect.insert
        await conn.execute(
            insert(CacheResource).values(key=record.key, endpoint=record.endpoint).on_conflict_do_nothing()
        )
        # The writers of a key take turns: each then sees the variants the previous one left.
        await conn.execute(select(CacheResource.key).where(CacheResource.key == record.key).with_for_update())

        superseded = CacheVariant.variant == record.variant
        superseded &= CacheVariant.key == record.key
        if replaces is not None:
            superseded |= CacheVariant.entry_id == replaces
        removed = await self._delete_variants(conn, superseded)

        await conn.execute(insert(CacheBody).values(digest=record.body_digest, data=body).on_conflict_do_nothing())
        await conn.execute(insert(CacheVariant).values(**{name: getattr(record, name) for name in _FIELDS}))

        evicted = (
            (
                await conn.execute(
                    select(CacheVariant.entry_id)
                    .where(CacheVariant.key == record.key)
                    .order_by(CacheVariant.stored_at.desc(), CacheVariant.variant.desc())
                    .offset(keep)
                )
            )
            .scalars()
            .all()
        )
        if evicted:
            removed += await self._delete_variants(conn, CacheVariant.entry_id.in_(evicted))

        await self._forget(conn, removed, added=[record])

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        async def delete_it(conn: AsyncConnection) -> bool:
            removed = await self._delete_variants(conn, CacheVariant.entry_id == entry_id)
            await self._forget(conn, removed)
            return bool(removed)

        return await self._write(delete_it)

    async def delete_key(self, key: str) -> int:
        async def delete_them(conn: AsyncConnection) -> int:
            removed = await self._delete_variants(conn, CacheVariant.key == key)
            await self._forget(conn, removed)
            return len(removed)

        return await self._write(delete_them)

    async def delete_stored_before(self, cutoff: float, *, limit: int) -> int:
        async def delete_them(conn: AsyncConnection) -> int:
            expired = (
                (
                    await conn.execute(
                        select(CacheVariant.entry_id)
                        .where(CacheVariant.stored_at < cutoff)
                        .order_by(CacheVariant.stored_at)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            # freshened since they were read: no longer expired
            removed = await self._delete_variants(
                conn, CacheVariant.entry_id.in_(expired) & (CacheVariant.stored_at < cutoff)
            )
            await self._forget(conn, removed)
            return len(removed)

        return await self._write(delete_them)

    async def list_keys(
        self, *, endpoint: Optional[str] = None, after: Optional[str] = None, limit: int = 100
    ) -> list[str]:
        query = select(CacheResource.key).order_by(CacheResource.endpoint, CacheResource.key).limit(limit)
        if endpoint is not None:
            query = query.where(CacheResource.endpoint == endpoint)
        if after is not None:
            query = query.where(tuple_(CacheResource.endpoint, CacheResource.key) > tuple_(endpoint_of(after), after))
        async with self.engine.connect() as conn:
            return list((await conn.execute(query)).scalars())

    async def stats(self) -> list[EndpointStats]:
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(CacheStats).order_by(CacheStats.endpoint))).all()
        return [EndpointStats(row.endpoint, row.entries, row.bytes) for row in rows]

    async def largest(self, *, endpoint: Optional[str] = None, limit: int = 10) -> list[VariantRecord]:
        query = select(CacheVariant.__table__).order_by(CacheVariant.body_size.desc()).limit(limit)
        if endpoint is not None:
            query = query.where(CacheVariant.endpoint == endpoint)
        async with self.engine.connect() as conn:
            return [_record(row) for row in (await conn.execute(query)).all()]

    async def body_digests(self) -> set[str]:
        async with self.engine.connect() as conn:
            return set((await conn.execute(select(CacheBody.digest))).scalars())

    async def _write(self, work: Callable[[AsyncConnection], Awaitable[T]]) -> T:
        """Run ``work`` in one transaction, again when it met a concurrent writer."""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                async with self.engine.begin() as conn:
                    return await work(conn)
            except (IntegrityError, DBAPIError) as exc:
                if attempt == ATTEMPTS or not _is_concurrency(exc):
                    raise
                logger.debug(f"Cache write met a concurrent writer, attempt {attempt}: {exc.__class__.__name__}")
                await asyncio.sleep(0.01 * attempt)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _delete_variants(self, conn: AsyncConnection, where) -> list[Row]:
        """Delete variants, and hand back the rows that went: what is left to forget about them."""
        return list(
            (
                await conn.execute(
                    delete(CacheVariant)
                    .where(where)
                    .returning(
                        CacheVariant.key, CacheVariant.endpoint, CacheVariant.body_digest, CacheVariant.body_size
                    )
                )
            ).all()
        )

    async def _forget(
        self, conn: AsyncConnection, removed: Sequence[Row], *, added: Iterable[VariantRecord] = ()
    ) -> None:
        """What follows variants being deleted (and added): resources and bodies nothing references, then counters.

        Counters come last, so the row of an endpoint is locked for the shortest time and never while waiting.
        """
        if removed:
            keys = {row.key for row in removed}
            await conn.execute(
                delete(CacheResource).where(
                    CacheResource.key.in_(keys), ~exists().where(CacheVariant.key == CacheResource.key)
                )
            )
            digests = {row.body_digest for row in removed}
            await conn.execute(
                delete(CacheBody).where(
                    CacheBody.digest.in_(digests), ~exists().where(CacheVariant.body_digest == CacheBody.digest)
                )
            )

        deltas: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in removed:
            deltas[row.endpoint][0] -= 1
            deltas[row.endpoint][1] -= row.body_size
        for record in added:
            deltas[record.endpoint][0] += 1
            deltas[record.endpoint][1] += record.body_size
        for endpoint in sorted(deltas):
            entries, size = deltas[endpoint]
            if entries or size:
                insert = self._dialect.insert(CacheStats).values(endpoint=endpoint, entries=entries, bytes=size)
                await conn.execute(
                    insert.on_conflict_do_update(
                        index_elements=[CacheStats.endpoint],
                        set_={
                            "entries": CacheStats.entries + insert.excluded.entries,
                            "bytes": CacheStats.bytes + insert.excluded.bytes,
                        },
                    )
                )
        if deltas:
            await conn.execute(delete(CacheStats).where(CacheStats.endpoint.in_(deltas), CacheStats.entries <= 0))


def _is_concurrency(exc: Exception) -> bool:
    """Whether the failure is one writer meeting another, which another attempt gets past."""
    if isinstance(exc, IntegrityError):
        return True
    return getattr(exc.orig, "sqlstate", None) in _RETRYABLE_SQLSTATES  # type: ignore[attr-defined]
