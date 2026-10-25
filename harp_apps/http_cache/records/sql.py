import asyncio
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from functools import partial
from typing import Optional, TypeVar

from sqlalchemy import ColumnElement, Row, and_, delete, exists, or_, select, tuple_
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.orm import aliased

from harp import get_logger
from harp_apps.http_cache.models import CacheBan, CacheBody, CacheCounter, CacheResource, CacheStats, CacheVariant

from .base import (
    Ban,
    BanKind,
    BanMode,
    CacheRecords,
    EndpointStats,
    Reclaimed,
    StoredVariant,
    VariantRecord,
    ban_prefixes,
    covered_ranges,
    endpoint_of,
)

logger = get_logger(__name__)

T = TypeVar("T")

#: How many times a write is attempted when it meets a concurrent one: a deadlock, or the delete of the last
#: reference to a body that a writer is taking.
ATTEMPTS = 5

#: SQLSTATE of a transaction PostgreSQL rolled back to break a deadlock, or to serialize it.
_RETRYABLE_SQLSTATES = ("40P01", "40001")

#: SQLSTATE of a foreign key violation.
_FOREIGN_KEY_SQLSTATE = "23503"

_FIELDS = tuple(column.name for column in CacheVariant.__table__.columns)


#: The row of the invalidation counter.
_COUNTER_ID = 1

#: The row of the floor under the stamps of new fills, beside the counter (see :meth:`SqlCacheRecords.reclaim`). Fills
#: lock it shared, so that raising it waits for the fills in flight.
_FLOOR_ID = 2


def _within(ban: Ban) -> ColumnElement[bool]:
    """Whether the key of a variant is one the ban covers: by range, so that the index of keys serves it."""
    ranges = []
    for low, high in covered_ranges(ban.kind, ban.prefix):
        if high is None:
            ranges.append(CacheVariant.key >= low)
        elif high == low + "\0":  # one key; and PostgreSQL has no NUL in a string
            ranges.append(CacheVariant.key == low)
        else:
            ranges.append(and_(CacheVariant.key >= low, CacheVariant.key < high))
    return or_(*ranges)


def _record(row: Row) -> VariantRecord:
    return VariantRecord(**{name: row._mapping[name] for name in _FIELDS}, stale=bool(row._mapping.get("stale")))


def _covers(key: str) -> ColumnElement[bool]:
    """Whether a ban covers a key: it is the ban of the key itself, or of one of the prefixes the key starts with."""
    return or_(
        and_(CacheBan.kind == BanKind.EXACT.value, CacheBan.prefix == key),
        and_(CacheBan.kind == BanKind.PREFIX.value, CacheBan.prefix.in_(ban_prefixes(key))),
    )


class SqlCacheRecords(CacheRecords):
    """The records in the storage database, tables ``http_cache_*`` (ADR-0014): shared by every instance of HARP."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    @property
    def _dialect(self):
        return {"postgresql": postgresql, "sqlite": sqlite}[self.engine.dialect.name]

    async def get_variants(self, key: str) -> list[StoredVariant]:
        newer_ban = CacheBan.seq > CacheVariant.stamp
        hard = exists().where(newer_ban, CacheBan.mode == BanMode.HARD.value, _covers(key))
        soft = exists().where(newer_ban, CacheBan.mode == BanMode.SOFT.value, _covers(key))
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(CacheVariant.__table__, CacheBody.data, soft.label("stale"))
                    .join(CacheBody, CacheBody.digest == CacheVariant.body_digest)
                    .where(CacheVariant.key == key, ~hard)
                    .order_by(CacheVariant.stored_at, CacheVariant.variant)
                )
            ).all()
        return [StoredVariant(_record(row), bytes(row.data)) for row in rows]

    async def counter(self) -> int:
        async with self.engine.connect() as conn:
            value = (await conn.execute(select(CacheCounter.value).where(CacheCounter.id == _COUNTER_ID))).scalar()
        return value or 0

    async def ban(self, kind: BanKind, prefix: str, mode: BanMode) -> Ban:
        async def append(conn: AsyncConnection) -> Ban:
            # The counter row stays locked until the ban commits: bans commit in the order of their numbers.
            insert = self._dialect.insert(CacheCounter).values(id=_COUNTER_ID, value=1)
            seq = (
                await conn.execute(
                    insert.on_conflict_do_update(
                        index_elements=[CacheCounter.id], set_={"value": CacheCounter.value + 1}
                    ).returning(CacheCounter.value)
                )
            ).scalar_one()
            ban = Ban(seq, kind, prefix, mode, time.time())
            await conn.execute(
                self._dialect.insert(CacheBan).values(
                    seq=seq, kind=kind.value, prefix=prefix, mode=mode.value, created_at=ban.created_at
                )
            )
            return ban

        return await self._write(append)

    async def bans(self) -> list[Ban]:
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(CacheBan).order_by(CacheBan.seq))).all()
        return [Ban(row.seq, BanKind(row.kind), row.prefix, BanMode(row.mode), row.created_at) for row in rows]

    async def reclaim(self, *, older_than: float, bans: int, entries: int) -> Reclaimed:
        await self._write(self._drop_superseded_bans)
        retired = deleted = 0
        hard = await self._old_bans(older_than, BanMode.HARD, bans + 1)
        pending, hard = len(hard) > bans, hard[:bans]
        if hard:
            retired, deleted, pending = await self._reclaim_hard(hard, entries, pending)

        # Soft bans retire nothing but themselves, and the ones that cannot yet are met again by every run: the whole
        # log is paged through, so that they never hide the ones behind them.
        after = 0
        while page := await self._old_bans(older_than, BanMode.SOFT, bans, after=after):
            retired += await self._reclaim_soft(page)
            after = page[-1].seq
        return Reclaimed(retired, deleted, pending)

    async def _reclaim_hard(self, hard: list[Ban], entries: int, pending: bool) -> tuple[int, int, bool]:
        # Before anything is deleted or retired: no new fill stamped below these bans, and the ones in flight stored.
        await self._write(partial(self._raise_floor, seq=max(ban.seq for ban in hard)))

        # Most exact bans cover nothing by now (their key was deleted when they were issued): retire those at once.
        gone = await self._write(partial(self._retire_exact_without_entries, bans=hard))
        retired, deleted = len(gone), 0
        for ban in hard:
            if ban.seq in gone:
                continue
            done, count = await self._write(partial(self._delete_covered, ban=ban, budget=entries - deleted))
            deleted += count
            if not done:
                pending = True
                continue
            await self._write(partial(self._retire, ban=ban))
            retired += 1
        return retired, deleted, pending

    async def _reclaim_soft(self, soft: list[Ban]) -> int:
        await self._write(partial(self._raise_floor, seq=max(ban.seq for ban in soft)))
        gone = await self._write(partial(self._retire_exact_without_entries, bans=soft))
        retired = len(gone)
        for ban in soft:
            # an exact ban that was not retired just now still has a stale entry
            if ban.kind is BanKind.EXACT or await self._write(partial(self._has_stale, ban=ban)):
                continue
            await self._write(partial(self._retire, ban=ban))
            retired += 1
        return retired

    async def _old_bans(self, older_than: float, mode: BanMode, limit: int, *, after: int = 0) -> list[Ban]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(CacheBan)
                    .where(CacheBan.created_at < older_than, CacheBan.mode == mode.value, CacheBan.seq > after)
                    .order_by(CacheBan.seq)
                    .limit(limit)
                )
            ).all()
        return [Ban(row.seq, BanKind(row.kind), row.prefix, BanMode(row.mode), row.created_at) for row in rows]

    @staticmethod
    async def _retire_exact_without_entries(conn: AsyncConnection, bans: list[Ban]) -> set[int]:
        """Retire the exact bans whose key holds nothing they cover. Tells which. Only after the floor was raised."""
        seqs = [ban.seq for ban in bans if ban.kind is BanKind.EXACT]
        if not seqs:
            return set()
        covered = exists().where(CacheVariant.key == CacheBan.prefix, CacheVariant.stamp < CacheBan.seq)
        result = await conn.execute(delete(CacheBan).where(CacheBan.seq.in_(seqs), ~covered).returning(CacheBan.seq))
        return set(result.scalars())

    @staticmethod
    async def _drop_superseded_bans(conn: AsyncConnection) -> None:
        """A ban is redundant when a newer one has the same kind, prefix and mode: whatever it covers, that covers."""
        newer = aliased(CacheBan)
        await conn.execute(
            delete(CacheBan).where(
                exists().where(
                    newer.kind == CacheBan.kind,
                    newer.prefix == CacheBan.prefix,
                    newer.mode == CacheBan.mode,
                    newer.seq > CacheBan.seq,
                )
            )
        )

    async def _raise_floor(self, conn: AsyncConnection, seq: int) -> None:
        # The row is locked until commit, once waited for every fill in flight (they hold it shared): what they stored
        # is visible to what comes next, and the fills that start after read the new floor.
        insert = self._dialect.insert(CacheCounter).values(id=_FLOOR_ID, value=seq)
        await conn.execute(
            insert.on_conflict_do_update(
                index_elements=[CacheCounter.id], set_={"value": insert.excluded.value}, where=CacheCounter.value < seq
            )
        )

    async def _read_floor(self, conn: AsyncConnection) -> int:
        """The floor under the stamps of new fills, the row of it locked shared until the end of the transaction."""
        query = select(CacheCounter.value).where(CacheCounter.id == _FLOOR_ID).with_for_update(read=True)
        floor = (await conn.execute(query)).scalar()
        if floor is None:
            # Never raised yet: have the row, to lock it, as a raise in flight would
            await conn.execute(
                self._dialect.insert(CacheCounter).values(id=_FLOOR_ID, value=0).on_conflict_do_nothing()
            )
            floor = (await conn.execute(query)).scalar()
        return floor

    async def _delete_covered(self, conn: AsyncConnection, ban: Ban, budget: int) -> tuple[bool, int]:
        """Delete at most ``budget`` of the variants a ban covers. Tells whether that was all of them, and how many."""
        stale = CacheVariant.stamp < ban.seq
        found = (
            await conn.execute(
                select(CacheVariant.entry_id, CacheVariant.key)
                .where(_within(ban), stale)
                .order_by(CacheVariant.key)
                .limit(budget + 1)
            )
        ).all()
        batch = found[:budget]
        if not batch:
            return len(found) <= budget, 0
        await self._lock_resources(conn, [row.key for row in batch])
        # freshened since they were read: no longer covered
        removed = await self._delete_variants(conn, CacheVariant.entry_id.in_([row.entry_id for row in batch]) & stale)
        await self._forget(conn, removed)
        return len(found) <= budget, len(removed)

    @staticmethod
    async def _has_stale(conn: AsyncConnection, ban: Ban) -> bool:
        """Whether a variant is left that the ban makes stale: stamped before it, in the keys it covers."""
        return bool((await conn.execute(select(exists().where(_within(ban), CacheVariant.stamp < ban.seq)))).scalar())

    @staticmethod
    async def _retire(conn: AsyncConnection, ban: Ban) -> None:
        await conn.execute(delete(CacheBan).where(CacheBan.seq == ban.seq))

    async def reclaim_orphans(self, *, limit: int) -> int:
        async def delete_them(conn: AsyncConnection) -> int:
            resources = (
                select(CacheResource.key).where(~exists().where(CacheVariant.key == CacheResource.key)).limit(limit)
            )
            gone = (await conn.execute(delete(CacheResource).where(CacheResource.key.in_(resources)))).rowcount
            bodies = (
                select(CacheBody.digest)
                .where(~exists().where(CacheVariant.body_digest == CacheBody.digest))
                .limit(limit)
            )
            return gone + (await conn.execute(delete(CacheBody).where(CacheBody.digest.in_(bodies)))).rowcount

        return await self._write(delete_them)

    async def _is_banned(self, conn: AsyncConnection, key: str, stamp: int) -> bool:
        """Whether a ban covers a key with a number above this stamp."""
        return bool((await conn.execute(select(exists().where(CacheBan.seq > stamp, _covers(key))))).scalar())

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        async with self.engine.connect() as conn:
            row = (await conn.execute(select(CacheVariant.__table__).where(CacheVariant.entry_id == entry_id))).first()
        return _record(row) if row else None

    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> bool:
        return await self._write(lambda conn: self._put(conn, record, body, keep, replaces))

    async def _put(
        self, conn: AsyncConnection, record: VariantRecord, body: bytes, keep: int, replaces: Optional[uuid.UUID]
    ) -> bool:
        # A fill that started before a ban that was retired since is refused: nothing hides what it stored anymore, and
        # reclamation (:meth:`reclaim`) waits for the fills that hold the floor row, before it deletes. A replacement is
        # not a fill: the variant it replaces is still there, so no retired ban covered it. Taken first, held to the end.
        if replaces is None and record.stamp < await self._read_floor(conn):
            return False
        # A ban that lands after this check still hides what is stored: lookups check bans too. This only spares the
        # write. It comes first, so that a refusal leaves no resource row behind.
        if await self._is_banned(conn, record.key, record.stamp):
            return False

        # Locks are taken resource first, then variants, by every writer: nobody waits for a row while holding one
        # that the owner of that row waits for.
        insert = self._dialect.insert
        if replaces is None:
            await conn.execute(
                insert(CacheResource).values(key=record.key, endpoint=record.endpoint).on_conflict_do_nothing()
            )
        # The writers of a key take turns: each then sees the variants the previous one left.
        locked = await self._lock_resources(conn, [record.key])
        if replaces is not None:
            # The variant being replaced was purged, or replaced by another writer, since it was read: what is being
            # written is older than that, and must not come back.
            gone = (
                not locked
                or not (
                    await conn.execute(select(CacheVariant.entry_id).where(CacheVariant.entry_id == replaces))
                ).first()
            )
            if gone:
                return False

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
        return True

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        async def delete_it(conn: AsyncConnection) -> bool:
            keys = (
                (await conn.execute(select(CacheVariant.key).where(CacheVariant.entry_id == entry_id))).scalars().all()
            )
            await self._lock_resources(conn, keys)
            removed = await self._delete_variants(conn, CacheVariant.entry_id == entry_id)
            await self._forget(conn, removed)
            return bool(removed)

        return await self._write(delete_it)

    async def delete_key(self, key: str) -> int:
        async def delete_them(conn: AsyncConnection) -> int:
            await self._lock_resources(conn, [key])
            removed = await self._delete_variants(conn, CacheVariant.key == key)
            await self._forget(conn, removed)
            return len(removed)

        return await self._write(delete_them)

    async def delete_stored_before(self, cutoff: float, *, limit: int) -> int:
        async def delete_them(conn: AsyncConnection) -> int:
            expired = (
                await conn.execute(
                    select(CacheVariant.entry_id, CacheVariant.key)
                    .where(CacheVariant.stored_at < cutoff)
                    .order_by(CacheVariant.stored_at)
                    .limit(limit)
                )
            ).all()
            await self._lock_resources(conn, [row.key for row in expired])
            # freshened since they were read: no longer expired
            removed = await self._delete_variants(
                conn, CacheVariant.entry_id.in_([row.entry_id for row in expired]) & (CacheVariant.stored_at < cutoff)
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
        return [EndpointStats(row.endpoint, row.entries, row.bytes, row.refused) for row in rows]

    async def count_refused(self, endpoint: str, count: int = 1) -> None:
        insert = self._dialect.insert(CacheStats).values(endpoint=endpoint, entries=0, bytes=0, refused=count)
        async with self.engine.begin() as conn:
            await conn.execute(
                insert.on_conflict_do_update(
                    index_elements=[CacheStats.endpoint], set_={"refused": CacheStats.refused + count}
                )
            )

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
                    if self.engine.dialect.name == "sqlite":
                        await self._take_the_write_lock(conn)
                    return await work(conn)
            except (IntegrityError, DBAPIError) as exc:
                if attempt == ATTEMPTS or not _is_concurrency(exc):
                    raise
                logger.debug(f"Cache write met a concurrent writer, attempt {attempt}: {exc.__class__.__name__}")
                await asyncio.sleep(0.01 * attempt)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _take_the_write_lock(self, conn: AsyncConnection) -> None:
        """SQLite: the driver opens a transaction at the first write, so what a writer read before it was read outside
        any transaction, and the floor (:meth:`reclaim`) could be raised and the ban retired in between. A write that
        changes nothing makes the transaction start here, holding the one write lock of the database, as the shared
        lock on the floor row does on PostgreSQL."""
        await conn.execute(self._dialect.insert(CacheCounter).values(id=_FLOOR_ID, value=0).on_conflict_do_nothing())

    async def _lock_resources(self, conn: AsyncConnection, keys: Iterable[str]) -> bool:
        """Lock the resource rows of these keys, in key order. Tells whether they all exist."""
        wanted = sorted(set(keys))
        if not wanted:
            return False
        locked = await conn.execute(
            select(CacheResource.key).where(CacheResource.key.in_(wanted)).order_by(CacheResource.key).with_for_update()
        )
        return len(locked.all()) == len(wanted)

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
            await conn.execute(
                delete(CacheStats).where(
                    CacheStats.endpoint.in_(deltas), CacheStats.entries <= 0, CacheStats.refused == 0
                )
            )


def _is_concurrency(exc: Exception) -> bool:
    """Whether the failure is one writer meeting another, which another attempt gets past.

    That is a deadlock PostgreSQL broke, or a foreign key violated because the body or resource it points at was
    deleted by the last record leaving it. Any other integrity error, a duplicate entry id for one, is a bug to raise.
    """
    orig = getattr(exc, "orig", None)
    if getattr(orig, "sqlstate", None) in _RETRYABLE_SQLSTATES:
        return True
    return isinstance(exc, IntegrityError) and (
        getattr(orig, "sqlstate", None) == _FOREIGN_KEY_SQLSTATE or "FOREIGN KEY constraint failed" in str(orig)
    )
