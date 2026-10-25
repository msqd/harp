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

## As implemented in the store (#1594)

- **The cache key is the endpoint and the path in clear, then a hash of the query.** hishel keys its storage by
  `sha256(url)`, which is opaque: nothing can be ordered or ranged by it. `AsyncCacheTransport` now keys by
  `<scheme>://<endpoint><path>`, followed by `?` and the sha256 of the whole query string as it came when there is one
  (a request keyed by its body adds its hash to it). Two different query values never share an entry, a path prefix
  is a range of keys (#1597), and no query value is in any table, since a query may hold a credential (ADR-0009). The
  query is also kept in `http_cache_variants.query`, for display only, with the values of the parameters in the
  request's redaction set replaced by `REDACTED`, and so is the url in the stored head. A response whose URL carries
  such a parameter is therefore cached (ADR-0009 withheld it); hishel matches an entry by its whole url, so the
  storage gives the entries it reads the url of the request being looked up when it differs from the stored one only
  by redacted values. A path over 2048 bytes is not cached (PostgreSQL refuses to index values past a third of a
  page): it is counted in `http_cache_stats.refused` and warned about once per endpoint. Only the hash of a low-entropy
  secret can be guessed from the key: that is accepted.
- **Tables** `http_cache_resources` (key, endpoint), `http_cache_variants` (primary key `(key, variant)`, unique
  `entry_id`, status, `vary`, body digest and size, instants, serialized heads), `http_cache_bodies` (digest, data)
  and `http_cache_stats` (endpoint, entries, bytes), in the `http_cache` alembic branch. Keys and resource endpoints
  are `COLLATE "C"` on PostgreSQL, so records list in `(endpoint, key)` order, bytewise.
- **`stamp` on variant records is reserved for the invalidation log** (#1596): the counter read before the origin
  fetch. It is stored as given, `0` until then; nothing reads it.
- **Counters** are updated in the transaction of each write, expiry and deletion, last, so the row of an endpoint is
  locked for the least time. The largest entries are read from an index on `(endpoint, body_size)`.
- **Writers of a key** take turns by locking its resource row (`SELECT … FOR UPDATE`). Every write locks the resource
  rows first and the variants after, whoever the writer is (store, purge, expiry sweep), so none waits for what the
  other holds. A write retries on a deadlock or a foreign key violated by the body or resource another writer just
  deleted; any other integrity error is raised. A 304 freshening replaces its variant only if it is still there: a
  copy read before a purge, or before another instance replaced it, does not come back.
- **Memory** keeps the same records in dictionaries and a sorted list, and is used when the storage application is not
  loaded. **Redis** blob storage no longer holds the cache: it is in the storage database until the Redis backend.
- **The old cache** (`cache/meta` blobs) is not read. The janitor sees it as orphan blobs and deletes it, after its
  grace period. During a rolling upgrade, an instance still on the old version keeps writing and reading blobs: the
  entries it stores are not seen by the new instances, and the janitor of a new instance deletes them once they are
  older than the grace. Those entries miss and are fetched again from the origin.

## Rejected

- **A derived index beside today's blobs.** Two stores to keep consistent, and prefix invalidation still
  scans blobs or trusts an index that may lag.
- **Eager deletion only.** Every invalidation costs as many deletes as matching entries, PostgreSQL pays
  for it in VACUUM, and soft invalidation needs a lookup-time check anyway.
- **Bans only, as Varnish does.** Lookups walk the whole ban list, and bans pile up (Varnish's
  `ban_cutoff` exists for that).
- **Generations per endpoint only.** O(1) for endpoint and everything, but no prefix invalidation.
