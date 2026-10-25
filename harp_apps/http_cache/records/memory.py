import time
import uuid
from bisect import bisect_left, bisect_right, insort
from dataclasses import replace
from typing import Optional

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
    endpoint_of,
)


class MemoryCacheRecords(CacheRecords):
    """The records in the process: lost at restart, not shared with other instances.

    Every method runs without yielding to the event loop, which is what makes it safe to run concurrently.
    """

    def __init__(self):
        #: ``(endpoint, key)`` of the keys that hold a variant, in bytewise order: what a range of keys is read from.
        self._keys: list[tuple[str, str]] = []
        self._variants: dict[str, dict[str, VariantRecord]] = {}
        self._by_id: dict[uuid.UUID, VariantRecord] = {}
        self._bodies: dict[str, bytes] = {}
        self._references: dict[str, int] = {}
        self._entries: dict[str, int] = {}
        self._bytes: dict[str, int] = {}
        self._refused: dict[str, int] = {}
        #: ``(stored_at, entry id)`` of every variant, oldest first: what expiry reads from the start.
        self._by_age: list[tuple[float, str]] = []
        self._counter = 0
        #: The last ban of each kind, prefix and mode: the only one that matters to a check.
        self._bans: dict[tuple[BanKind, str, BanMode], Ban] = {}
        #: Fills stamped below it are refused: bans up to this number may have been retired, see :meth:`reclaim`.
        self._floor = 0

    async def get_variants(self, key: str) -> list[StoredVariant]:
        hard, soft = self._newest_ban(key, BanMode.HARD), self._newest_ban(key, BanMode.SOFT)
        return [
            StoredVariant(replace(record, stale=soft > record.stamp), self._bodies[record.body_digest])
            for record in self._oldest_first(key)
            if hard <= record.stamp
        ]

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        return self._by_id.get(entry_id)

    async def counter(self) -> int:
        return self._counter

    async def ban(self, kind: BanKind, prefix: str, mode: BanMode) -> Ban:
        self._counter += 1
        ban = self._bans[kind, prefix, mode] = Ban(self._counter, kind, prefix, mode, time.time())
        return ban

    async def bans(self) -> list[Ban]:
        return sorted(self._bans.values(), key=lambda ban: ban.seq)

    def _newest_ban(self, key: str, mode: BanMode) -> int:
        """The number of the last ban of this mode that covers a key, ``0`` when none does."""
        covering = [self._bans.get((BanKind.EXACT, key, mode))]
        covering += (self._bans.get((BanKind.PREFIX, prefix, mode)) for prefix in ban_prefixes(key))
        return max((ban.seq for ban in covering if ban), default=0)

    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> bool:
        if max(self._newest_ban(record.key, mode) for mode in BanMode) > record.stamp:
            return False
        # A fill that started before a retired ban may be covered by it. A replacement is not a fill: the variant it
        # replaces is still there, so no retired ban covered it.
        if replaces is None and record.stamp < self._floor:
            return False
        if replaces is not None:
            if replaces not in self._by_id:
                return False
            self._remove(self._by_id[replaces])
        self._remove(self._variants.get(record.key, {}).get(record.variant))

        self._bodies[record.body_digest] = body
        self._references[record.body_digest] = self._references.get(record.body_digest, 0) + 1
        if record.key not in self._variants:
            insort(self._keys, (record.endpoint, record.key))
        self._variants.setdefault(record.key, {})[record.variant] = record
        self._by_id[record.entry_id] = record
        insort(self._by_age, (record.stored_at, str(record.entry_id)))
        self._entries[record.endpoint] = self._entries.get(record.endpoint, 0) + 1
        self._bytes[record.endpoint] = self._bytes.get(record.endpoint, 0) + record.body_size

        for evicted in self._oldest_first(record.key)[:-keep] if keep > 0 else self._oldest_first(record.key):
            self._remove(evicted)
        return True

    async def reclaim(self, *, older_than: float, bans: int, entries: int) -> Reclaimed:
        old = sorted((ban for ban in self._bans.values() if ban.created_at < older_than), key=lambda ban: ban.seq)
        all_hard = [ban for ban in old if ban.mode is BanMode.HARD]
        # every soft ban is checked, stuck ones included: they must not hide the ones behind them
        hard, soft = all_hard[:bans], [ban for ban in old if ban.mode is BanMode.SOFT]
        if hard or soft:
            self._floor = max(self._floor, *(ban.seq for ban in hard + soft))

        retired = deleted = 0
        pending = len(all_hard) > bans
        for ban in hard:
            covered = [record for record in self._covered(ban) if record.stamp < ban.seq]
            budget = entries - deleted
            for record in covered[:budget]:
                self._remove(record)
            deleted += min(len(covered), budget)
            if len(covered) > budget:
                pending = True
                continue
            self._retire(ban)
            retired += 1
        for ban in soft:
            if not any(record.stamp < ban.seq for record in self._covered(ban)):
                self._retire(ban)
                retired += 1
        return Reclaimed(retired, deleted, pending)

    def _covered(self, ban: Ban) -> list[VariantRecord]:
        """The variants a ban covers, whatever their stamp."""
        start, stop = 0, len(self._keys)
        if ban.prefix:
            endpoint = endpoint_of(ban.prefix)
            start, stop = bisect_left(self._keys, (endpoint, "")), bisect_left(self._keys, (endpoint + "\0", ""))
        keys = (key for _, key in self._keys[start:stop])
        if ban.kind is BanKind.EXACT:
            keys = (key for key in keys if key == ban.prefix)
        else:
            keys = (key for key in keys if ban.prefix in ban_prefixes(key))
        return [record for key in keys for record in self._variants[key].values()]

    def _retire(self, ban: Ban) -> None:
        del self._bans[ban.kind, ban.prefix, ban.mode]

    async def reclaim_orphans(self, *, limit: int) -> int:
        return 0  # bodies are reference counted: none outlives its last variant

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        record = self._by_id.get(entry_id)
        self._remove(record)
        return record is not None

    async def delete_key(self, key: str) -> int:
        records = self._oldest_first(key)
        for record in records:
            self._remove(record)
        return len(records)

    async def delete_stored_before(self, cutoff: float, *, limit: int) -> int:
        expired = self._by_age[: min(limit, bisect_left(self._by_age, (cutoff, "")))]
        for _, entry_id in expired:
            self._remove(self._by_id[uuid.UUID(entry_id)])
        return len(expired)

    async def list_keys(
        self, *, endpoint: Optional[str] = None, after: Optional[str] = None, limit: int = 100
    ) -> list[str]:
        start, stop = 0, len(self._keys)
        if endpoint is not None:
            start, stop = bisect_left(self._keys, (endpoint, "")), bisect_left(self._keys, (endpoint + "\0", ""))
        if after is not None:
            start = max(start, bisect_right(self._keys, (endpoint_of(after), after)))
        return [key for _, key in self._keys[start : min(stop, start + limit)]]

    async def stats(self) -> list[EndpointStats]:
        return [
            EndpointStats(
                endpoint, self._entries.get(endpoint, 0), self._bytes.get(endpoint, 0), self._refused.get(endpoint, 0)
            )
            for endpoint in sorted(self._entries.keys() | self._refused.keys())
        ]

    async def count_refused(self, endpoint: str, count: int = 1) -> None:
        self._refused[endpoint] = self._refused.get(endpoint, 0) + count

    async def largest(self, *, endpoint: Optional[str] = None, limit: int = 10) -> list[VariantRecord]:
        records = (r for r in self._by_id.values() if endpoint is None or r.endpoint == endpoint)
        return sorted(records, key=lambda r: r.body_size, reverse=True)[:limit]

    async def body_digests(self) -> set[str]:
        return set(self._bodies)

    def _oldest_first(self, key: str) -> list[VariantRecord]:
        return sorted(self._variants.get(key, {}).values(), key=lambda record: (record.stored_at, record.variant))

    def _remove(self, record: Optional[VariantRecord]) -> None:
        if record is None:
            return
        variants = self._variants[record.key]
        del variants[record.variant]
        if not variants:
            del self._variants[record.key]
            del self._keys[bisect_left(self._keys, (record.endpoint, record.key))]
        del self._by_id[record.entry_id]
        del self._by_age[bisect_left(self._by_age, (record.stored_at, str(record.entry_id)))]

        self._references[record.body_digest] -= 1
        if not self._references[record.body_digest]:
            del self._references[record.body_digest]
            del self._bodies[record.body_digest]

        self._entries[record.endpoint] -= 1
        self._bytes[record.endpoint] -= record.body_size
        if not self._entries[record.endpoint]:
            del self._entries[record.endpoint]
            del self._bytes[record.endpoint]
