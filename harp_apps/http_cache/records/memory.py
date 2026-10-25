import uuid
from bisect import bisect_left, bisect_right, insort
from typing import Optional

from .base import CacheRecords, EndpointStats, StoredVariant, VariantRecord, endpoint_of


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

    async def get_variants(self, key: str) -> list[StoredVariant]:
        return [StoredVariant(record, self._bodies[record.body_digest]) for record in self._oldest_first(key)]

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        return self._by_id.get(entry_id)

    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> None:
        if replaces is not None:
            if replaces not in self._by_id:
                return
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
