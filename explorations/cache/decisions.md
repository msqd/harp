# explore/cache: decisions from the grill

Decisions taken while grilling explore/cache (2026-10-25). Built on explore/audit (which includes
explore/auth). Brainstorm: `explorations/brainstorm.md`, section Cache explorer.

Facts from the code: one `cache/meta` blob per cache key (blob id = the key, the URL with its host
replaced by the endpoint name), holding the variants of a `Vary` resource
(`harp_apps/http_cache/adapters.py:55-60, 155`); bodies in separate blobs; SQL, memory and Redis blob
storages all enumerate by content type (`iter_blobs`); a transaction records only `cached` and the
age (`harp_apps/proxy/controllers.py:336-338`), but its cache key can be recomputed from its endpoint
and URL.

1. Vocabulary: Cache Entry, Variant, Invalidation (decided by someone, audited when an account
   decided), Expiry (no one decided: lifetime, or RFC 9111 invalidation by an unsafe request).
2. (Superseded by 4.) Index: `http_cache_entries` (SQL, http_cache app prefix) is derived, never the truth. Updated
   best-effort after each cache write; caught up by a periodic `iter_blobs` scan run by the janitor,
   and on demand by an Editor. The explorer lists from it and may lag; opening an entry reads its
   blob. The cache never depends on SQL, even on Redis.
3. (Closed by 4.) Invalidation scopes are not decided: scanning blobs may cost a lot. Before any
   modelling decision, a spike studies how mature caches model storage and invalidation (Varnish and
   others, open source and commercial with published architecture) and the algorithmic options,
   aiming for the ideal data structure rather than workarounds on today's model. Pre-1.0, losing the
   cache at upgrade is acceptable, so migration does not constrain the model (user, 2026-10-25).
4. Model (from the spike, `explorations/cache/research/systems.md` and `algorithms.md`, which
   converge): the store itself is indexed on every backend, one row per resource and one per
   variant (Varnish objhead/objcore, Pingora primary + variance), ordered by endpoint and path
   (PostgreSQL tables with a `COLLATE "C"` key, Redis hashes and lex sorted sets, in-memory
   structures). Invalidation appends to a numbered invalidation log (bans: exact key, prefix cut at
   path segments, endpoint, all), O(1) to issue, checked at lookup in the same round trip and at
   store time. Each entry is stamped with the invalidation counter read before its origin fetch
   (memcache leases generalised to prefixes), kept in the shared store so it holds across instances;
   bans are numbered by a counter row (`UPDATE … RETURNING`), not a sequence. A background worker
   deletes matching entries by range, then retires the ban ("lazy at once, eager in background").
   Bodies are content-addressed. Statistics come from counters kept on write. A transaction records
   its cache key, variant id and seq to link to the entry that served it. Redis requires a
   `volatile-*` eviction policy, else bans can be evicted. Replaces hishel's storage adapter; the
   existing cache is dropped at upgrade. Delivered in two steps: indexed rows with endpoint and
   all invalidation, then prefix bans and the reclamation worker. ADR to write.
5. Both invalidation modes (RFC 9111 §4.4), soft by default: soft marks entries stale and keeps
   validators, so the next request revalidates (`304` reuses the body); hard makes them unusable.
   The mode is a field of the ban; the explorer offers a "hard" checkbox; the audit event records it.
6. A transaction records its cache outcome (hit, stale, revalidated, miss, not cacheable), cache
   key, variant id and the invalidation seq in force: #404 moves from 0.14 to explore/cache, since
   the new store produces them. #801 (PURGE with an IP allow-list) stays in 0.13 (building) on
   today's store; explore/cache re-implements it as a ban.
