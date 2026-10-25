# ADR-0014: The cache store is indexed, and invalidation is a numbered log checked at lookup

- **Status**: proposed
- **Date**: 2026-10-25
- **Decided in**: [explore/cache](https://github.com/msqd/harp/milestone/27)

**Proposed on the explore/cache exploration branch; nothing of it is implemented.** Line references are
to `main` when this record was written. The research behind it is in
`explorations/cache/research/systems.md` and `explorations/cache/research/algorithms.md`.

The cache keeps one record per resource and one per variant, ordered by endpoint and path, in every
storage backend. Removing entries is decided by appending a ban to a numbered invalidation log, which
lookups check; a background worker then deletes what the ban covers and retires it.

## Why the current model cannot serve an explorer

Today one `cache/meta` blob per cache key holds the list of its variants
(`harp_apps/http_cache/adapters.py:55-60, 155`), and blobs are found only by id or by enumerating a
content type. Listing entries per endpoint, invalidating a URL prefix or an endpoint, and counting
entries all mean scanning every stored blob. One blob per key with a variant list is also the shape
Apache Traffic Server names as its contention point, and the one that loses concurrent updates in
Souin's Redis backend. No classic engine (Varnish, ATS, nginx, Squid, Envoy) can list its entries:
they index by opaque hash, and Cloudflare had to add a per-machine index to find entries by host or tag.

## The model

- **Records.** A resource record per cache key, a variant record per `Vary` combination under it,
  ordered by endpoint then path: PostgreSQL tables keyed with `COLLATE "C"`, Redis hashes and lex sorted
  sets, in-memory structures. Bodies are stored by content digest, shared between variants that carry
  the same body.
- **Invalidation log.** An exact key, a URL prefix (cut at path segments), an endpoint or everything is
  one ban `(seq, kind, prefix, mode)`, O(1) to issue. Endpoint and everything are prefix bans, since the
  cache key's host is the endpoint name. `mode` is soft (stale, revalidate, RFC 9111 §4.4) or hard
  (unusable).
- **Lookup.** The ban check runs in the same round trip as the lookup (`NOT EXISTS` in PostgreSQL, a
  Lua script in Redis, a dictionary in memory), at a cost bounded by the key's depth, never by the
  number of entries or bans.
- **The fill race.** A fetch that started before an invalidation must not store its response after it.
  Each entry is stamped with the invalidation counter read before its origin fetch, kept in the shared
  store so the guarantee holds across instances; a store with a stamp below a matching ban is refused.
  Bans are numbered by a counter row (`UPDATE … RETURNING`), not a PostgreSQL sequence, so they commit
  in order.
- **Reclamation.** A background worker deletes, by range, what each ban covers, then retires the ban.
  Bans never pile up ("lazy at once, eager in background").
- **Statistics** come from counters kept on write, and the largest entries from an index on size.
- **Redis** must run with a `volatile-*` eviction policy; otherwise eviction can drop the bans and
  invalidated entries come back.

The store replaces the adapter HARP gives hishel today. The existing cache is dropped at upgrade, which
is accepted before 1.0.

## Rejected

- **A derived index beside today's blobs.** Two stores to keep consistent, and prefix invalidation still
  scans blobs or trusts an index that may lag.
- **Eager deletion only.** Every invalidation costs as many deletes as matching entries, PostgreSQL pays
  for it in VACUUM, and soft invalidation needs a lookup-time check anyway.
- **Bans only, as Varnish does.** Lookups walk the whole ban list, and bans pile up (Varnish's
  `ban_cutoff` exists for that).
- **Generations per endpoint only.** O(1) for endpoint and everything, but no prefix invalidation.
