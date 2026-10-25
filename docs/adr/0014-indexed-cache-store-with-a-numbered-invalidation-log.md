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
  page): it is counted in `http_cache_stats.refused` and warned about once per endpoint. **Accepted risk:** the hash is a
  plain sha256 (no secret salt, so that every instance computes the same key), hence a low-entropy secret in the
  query could be guessed from a dump of the database by hashing candidates. This ADR supersedes ADR-0009 on one
  point for the cache: ADR-0009 withheld responses to URLs with a redacted query parameter, they are now cached.
- **Tables** `http_cache_resources` (key, endpoint), `http_cache_variants` (primary key `(key, variant)`, unique
  `entry_id`, status, `vary`, body digest and size, instants, serialized heads), `http_cache_bodies` (digest, data)
  and `http_cache_stats` (endpoint, entries, bytes), in the `http_cache` alembic branch. Keys and resource endpoints
  are `COLLATE "C"` on PostgreSQL, so records list in `(endpoint, key)` order, bytewise.
- **`stamp` on variant records** is the invalidation counter read before the origin fetch (#1596, below).
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

## As implemented in the invalidation log (#1596)

- **Tables** `http_cache_bans` `(seq, kind, prefix, mode, created_at)`, primary key `seq`, index `(prefix, seq)`, and
  `http_cache_counter`, one row holding the number of the last ban. `kind` is `exact` (the prefix is the whole cache
  key, query hash included) or `prefix`. An endpoint is a `prefix` ban on `scheme://endpoint/`, one per scheme
  (`http`, `https`), and everything is the empty prefix. A path prefix (#1597) is a `prefix` ban cut after a `/`; the
  lookup already tests every such prefix of a key (`ban_prefixes`), so only the issuing and the reclamation remain.
- **Numbering** is `INSERT … ON CONFLICT DO UPDATE SET value = value + 1 RETURNING value` on the counter row, in the
  transaction that inserts the ban, so the row stays locked until the ban commits: bans commit in order, and a counter
  read by a fetch has every lower ban visible. The row is created by that first upsert, which is what lets SQLite (never
  migrated) work.
- **Lookup** returns the variants of a key that no *hard* ban covers with a number above their stamp, in the same
  statement (`NOT EXISTS`), and flags `stale` those a *soft* ban covers. The storage shows a stale variant to hishel as
  never fresh, the mechanism already used for entries kept for revalidation, so the origin is asked with the validators.
  Memory keeps the highest number per `(kind, prefix, mode)` and checks the key's prefixes. Both are O(depth of the key).
- **The stamp** is read in `AsyncCacheTransport.request_sender`, just before the request goes upstream (a miss or a
  revalidation), and handed to the storage in a context variable (`FETCH_STAMP`): hishel gives `update_entry` no
  request. Hits do not read it. A new entry carries it; a 304 raises the stamp of the variant to the stamp of the
  revalidating fetch if higher, which is what makes a soft-banned entry fresh again. When the counter cannot be read
  the stamp is `0`, which every ban is above. The read is not cached: one primary key lookup per origin fetch.
- **The fill race** is refused twice: `put` returns `False` before writing when a ban covers the key above the record's
  stamp (a store, or a 304 freshening), and the lookup hides or marks stale what got stored in the window between the
  check and the commit. The second is what the correctness rests on; the first spares a dead row.
- **Unsafe-method invalidation and `PURGE`** are a hard `exact` ban on the cache key, and delete its variants as
  before. `PURGE` bans whether or not it found an entry, since a first fetch may be in flight. **Each successful unsafe
  request therefore adds one ban per invalidated URI (the target, `Location`, `Content-Location`), and each `PURGE`
  one, until reclamation (#1597) retires them.**
- **Failures.** `AsyncStorage.invalidate`, `invalidate_endpoint` and `invalidate_all` raise `InvalidationError` when a
  ban cannot be recorded: an invalidation somebody asked for is never reported done when it was not (`PURGE` answers
  `503`); a hard invalidation whose ban failed still deletes the key's variants, best effort. A hard ban whose delete fails is recorded, hence done, and the failure is logged. The automatic invalidation
  after a write catches the error and logs it: the response is ready and must not break (#1272).
- **A soft ban is always revalidated.** Presented as a past `Date` alone, an entry fresh by `Expires` or by a huge
  `max-age` stayed fresh in hishel, and `allow_stale` served it as it was. A soft-banned entry is now shown with
  `Cache-Control: max-age=0, must-revalidate, x-harp-shown` and no `Expires`, its own values kept in `x-harp-stored-*`
  headers and put back after the 304 unless the 304 states them again (the extra directive is what tells HARP's value
  from an origin's `max-age=0, must-revalidate`). Origin responses lose every `x-harp-*` header before anything is
  stored. Entries kept only for their validator (heuristics off) are
  shown as before, by `Date` alone: `allow_stale` may still serve them.
- **Endpoint names** are spelled as httpx spells the host of a cache key (lowercase) in endpoint bans.
- **Not in this step:** bans on endpoint and everything are issued by `AsyncStorage.invalidate_endpoint` and
  `invalidate_all`, with nothing yet calling them (#1599). Entries they cover are not deleted until the ttl sweep
  removes them, and no ban is retired: reclamation (#1597) is what stops the log growing, one row per unsafe request
  until then. The Redis records (#1595) implement `CacheRecords.counter`, `ban`, and the ban check of `get_variants`
  and `put`.

## As implemented in prefix bans and reclamation (#1597)

- **A path ban** is a `prefix` ban whose prefix has no trailing `/`: `scheme://endpoint/api/users` covers the resource at
  that path whatever its query, and everything under `scheme://endpoint/api/users/`, not `/api/usersx`. One per scheme,
  like an endpoint ban (`AsyncStorage.invalidate_prefix`, the root being the endpoint ban). A prefix with a trailing `/`
  stays a directory (endpoint bans). To cover the path itself, `ban_prefixes(key)` now lists, for each directory of the
  key, the form with and without the `/`, and the path: twice the depth plus two reads, still independent of the number of
  entries and bans. `covered_ranges(kind, prefix)` is the same coverage seen from the ban, as ranges of keys
  (`[p, p[:-1]+"0")` for a directory; for a path, the path itself, `p/…` and `p?…`), which is what reclamation deletes by
  range on the key index. A test checks both agree on a corpus of keys.
- **Reclamation** is `CacheRecords.reclaim(older_than, bans, entries)`, one bounded run, stateless (what is left in the
  tables is the state to resume from), run by the janitor as a sweep registered by the `http_cache` application
  (`AsyncStorage.reclaim`: rounds of 500 deletions, 1000 bans of each mode, 20 rounds at most), or by the cache storage's
  own sweep when there is no janitor. A ban is taken once it is older than five minutes (`reclamation.grace`).
    - **Hard ban**: delete in batches, by key range, the variants stamped below the ban (locking the resource rows in key
      order, then `_forget` for bodies, resources and counters, as every deletion does, so counters stay exact), then
      retire the ban when a batch finds nothing more.
    - **Exact bans** (one per unsafe request and `PURGE`, whose entries were deleted when they were issued) are retired in
      one statement per round when nothing they cover is left, so that reclamation keeps up with the writes.
    - **Soft ban**: nothing is deleted, its entries are to be revalidated, which is the point of soft. It is retired when
      no variant is left in its range stamped below it: revalidated (a 304 raises the stamp to the fetch's), replaced,
      expired by the `ttl` sweep or deleted. Until then it costs a ban in the log and keeps the entries stale, which is
      what it is for. With no `ttl`, a soft ban on entries nobody asks for again stays for ever. Considered and
      rejected: marking the entries stale in their rows (a column, a migration and a Redis counterpart) so as to retire
      at once; deleting them (it defeats the soft ban).
      Soft bans that cannot be retired are met by every run, so the log of soft bans is paged through whole (by number),
      and they never hide the retirable ones behind them.
    - **Redundant bans**: a ban is dropped, at any age, when a newer one has the same kind, prefix and mode: whatever the
      older covers, the newer does, so lookups and refusals are unchanged. This keeps repeated invalidations of one
      prefix, soft ones above all, to one row. Memory keeps only the newest per `(kind, prefix, mode)` already.
    - **Orphans**: bodies and resources no variant refers to are deleted by `reclaim_orphans`. The store does not produce
      them (every write is one transaction); this is the safety net. A writer that meets the deletion of a body it just
      reused retries on the foreign key violation, as it does when the last variant leaves.
- **A retired ban never lets back a covered entry**, reasoned against the fill stamp. A fill stamped `t` is covered by a
  ban numbered `s > t`. Before retirement the ban refuses the fill (`put` checks it) and hides what slipped past that
  check (lookups check it). After it, nothing does, so a fill that a retired ban would have covered must not be stored.
  A **floor** under stamps, one row of the counter table (`id = 2`), refuses a *new fill* stamped below it. A run raises
  the floor to the highest ban it is about to reclaim, **before** it deletes anything. A fill stamped at or above `s`
  read the counter after the ban `s` committed (bans commit in the order of their numbers), so a retired `s` never
  covered it. That leaves the fills in flight when the floor is raised: one that passed the floor check and commits
  afterwards would not be seen by the deletion. So every fill reads the floor row `FOR SHARE` as the first statement of
  its transaction, held until commit, and raising the floor updates that row: it waits for the fills in flight to commit
  (the deletion then sees them, and deletes them if covered) and the fills that start after read the new floor (and are
  refused if covered). Fills do not block one another, nor bans (which lock the other counter row). When the floor row
  does not exist yet (nothing was ever retired) a fill creates it (`ON CONFLICT DO NOTHING`) before locking it, so a first
  raise cannot miss it. A 304 freshening (`replaces` given) is not a fill: the variant it replaces is still there, which
  means no retired ban covered it (it would have been deleted), and for a soft ban the check for stale variants and the
  replacement are atomic. A fill refused for the floor is served and not cached; so is one whose counter could not be
  read (stamp `0`) once any ban was retired. A fill refused though no retired ban covered it is the price of the floor
  being a single number: it happens only to a fetch that outlasts the grace, which is why bans are not taken younger.
  The cost is a shared row lock on one row per fill, and `SELECT … FOR SHARE` writes to the page. On SQLite
  the lock clause is a no-op, and the driver opens a transaction only at the first write, so a fill's reads would be
  outside any transaction: every cache write transaction therefore starts with a write that changes nothing (an
  `INSERT … ON CONFLICT DO NOTHING` of the floor row), which takes the one write lock of the database, as the shared
  lock does on PostgreSQL. A test on a SQLite file covers it.
- **Memory** keeps the same rules in the process: the floor is an integer, the newest ban per `(kind, prefix, mode)`.
- **Redis** (#1595) has to implement `bans`, `reclaim` and `reclaim_orphans`, and the floor, in its scripts.

## Rejected

- **A derived index beside today's blobs.** Two stores to keep consistent, and prefix invalidation still
  scans blobs or trusts an index that may lag.
- **Eager deletion only.** Every invalidation costs as many deletes as matching entries, PostgreSQL pays
  for it in VACUUM, and soft invalidation needs a lookup-time check anyway.
- **Bans only, as Varnish does.** Lookups walk the whole ban list, and bans pile up (Varnish's
  `ban_cutoff` exists for that).
- **Generations per endpoint only.** O(1) for endpoint and everything, but no prefix invalidation.
