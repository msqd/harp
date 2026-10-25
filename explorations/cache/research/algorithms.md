# Cache store algorithms: invalidation, expiry, browsing, statistics

Research input for the explore/cache spike (decision 3 in `explorations/cache/decisions.md`): which
data structures give an HTTP cache store cheap and correct lookup with `Vary` variants, insert and
replace, expiry, invalidation by exact key, URL prefix, named group (endpoint) and everything,
browsing, statistics, and a link from a recorded transaction to the entry that served it. Backends:
PostgreSQL (production), SQLite (dev), Redis, in-process memory; one to a few HARP instances; up to
millions of entries. Pre-1.0: the cache may be dropped at upgrade, so nothing below is constrained
by today's blob layout.

Sources are primary: RFCs, papers (publisher DOI checked against Crossref on 2026-10-25),
maintainers' documentation and design notes. Statements marked **Analysis** are this report's own
derivations from those sources, not quotes; they say so instead of borrowing a citation.

Notation: `n` entries, `m` entries matched by an invalidation, `b` live invalidation records
("bans"), `d` candidate prefixes of a key (its path-segment depth, plus host and root), `v`
variants of one key, `t` tags on one entry.

## Strongest findings

1. **Lazy invalidation by sequenced bans makes every scope O(1) to issue and O(d) to check,
   with no scan on the request path.** Varnish checks an object only against bans newer than the
   object, at hit time, and a background "ban lurker" removes matches later; bans older than the
   oldest object are discarded ([Varnish purging guide][varnish-purge]). Restricting ban prefixes
   to path-segment boundaries turns the check into `d` exact lookups in a hash or B-tree, instead
   of evaluating every ban (**Analysis**, §2.2).
2. **The stale-set race is the real correctness problem, and the fix is a version stamp taken
   before the origin fetch, not at store time.** Facebook's memcache uses a 64-bit lease token
   that a delete invalidates, so a set carrying a dead token is refused, "similar to how
   load-link/store-conditional operates" ([Nishtala et al., NSDI 2013, §3.2.1][fb-memcache]).
   Stamping each entry with the invalidation counter read *before* fetching gives the same
   guarantee for prefix, group and global scopes, and a stale (lower) read of the counter is
   still safe (**Analysis**, §3).
3. **The bans must live in the same store as the entries, and be checked in the same round trip.**
   PostgreSQL: a `NOT EXISTS` sub-select in the lookup query. Redis: a Lua script, which Redis
   executes atomically ([Redis Lua scripting][redis-lua]). Memory: a local dict. Sharing fate with
   the entries means a lost Redis loses bans and entries together (**Analysis**, §9).
4. **Eager deletion then becomes space reclamation only**, so it may be slow, batched and
   approximate: a B-tree range scan in SQL, plain `SCAN MATCH` in Redis (O(1) per call, O(N) per
   full iteration, guaranteed to return every key present throughout
   ([Redis SCAN][redis-scan])). Redis needs no secondary index at all for serving and invalidating.
5. **Expiry should be a removal deadline distinct from freshness.** RFC 9111 lets a stale stored
   response be validated or served stale under explicit permission (§4.2.4, §4.3), and
   "invalidate" may mean "mark invalid and in need of a mandatory validation" rather than delete
   (§4.4) ([RFC 9111][rfc9111]). A soft ban (force revalidation) keeps validators and saves origin
   bandwidth.
6. **Statistics come from counters maintained on write, plus indexes for top-k**; sketches
   (Count-Min ([Cormode and Muthukrishnan 2005][cms]), Space-Saving ([Metwally et al.
   2005][spacesaving])) only for hot-key detection, where exact per-key counters would cost a write
   per hit.

## 1. Operations and what the RFC fixes

- **Primary key.** "The cache key is composed from, at a minimum, the request method and target
  URI" ([RFC 9111 §2][rfc9111]). HARP's key is the URL with its host replaced by the endpoint name
  (decisions.md, facts), so the endpoint is the key's authority: a named group *is* a key prefix.
- **Secondary key (variants).** A stored response with `Vary` may be used only if every request
  header it nominates matches the original request, after allowed normalization (whitespace,
  line combining, semantic normalization); an absent header matches only an absent header; a
  `Vary` containing `*` "always fails to match"; when several match, the most recent by `Date` is
  chosen ([RFC 9111 §4.1][rfc9111]).
- **Invalidation by unsafe methods.** A cache "MUST invalidate the target URI" after a 2xx or 3xx
  response to an unsafe method, MAY invalidate `Location` and `Content-Location`, and MUST NOT do
  so across origins ([RFC 9111 §4.4][rfc9111]). This is an exact-key invalidation of all variants
  of the key.
- **Freshness.** Lifetime from `s-maxage` (shared caches), then `max-age`, then `Expires - Date`
  ([RFC 9111 §4.2.1][rfc9111]); stale responses may be revalidated (§4.3) and freshened by a 304
  (§4.3.4). The operator TTL is an additional cap on retention.

## 2. Invalidation strategies

### 2.1 Eager deletion through a secondary index

Delete every matching entry when the invalidation is issued, finding them through an index.

| Scope | PostgreSQL | Redis | Memory |
|---|---|---|---|
| Exact key | `DELETE ... WHERE key = ?`: O(log n) B-tree descent ([Comer 1979][btree]) | `DEL`/`UNLINK` O(1) per key | dict delete O(1) |
| Prefix | range `key >= p AND key < succ(p)`: O(log n + m) | lex sorted set `ZRANGE ... BYLEX`: O(log N + M) ([ZRANGEBYLEX][redis-zrangebylex]), then `UNLINK` each | sorted structure, O(log n + m) |
| Group (tag) | inverted index table `(tag, key)`: O(log n + m) | one set per tag, `SMEMBERS` + `UNLINK`: O(m) | dict tag→set: O(m) |
| All | `TRUNCATE`, or drop partitions | `UNLINK` of a namespace, or flush a dedicated DB | `clear()` |

- **PostgreSQL range on text keys.** A B-tree with the default operator class serves `LIKE 'p%'`
  only under the C collation; otherwise it needs `text_pattern_ops`, which in turn cannot serve
  `<`/`>` ([PostgreSQL operator classes][pg-opclass]). **Analysis:** declare the key column
  `COLLATE "C"` and query by explicit range rather than `LIKE`, which also removes the need to
  escape `%` and `_` in operator-supplied prefixes.
- **SQLite.** The `LIKE` optimization applies only under specific collation and
  `case_sensitive_like` conditions ([SQLite optimizer §5][sqlite-like]); an explicit range on a
  `BINARY`-collated column avoids depending on them (**Analysis**).
- **Redis lex ranges.** `ZRANGEBYLEX` orders members by `memcmp()` and is only defined when all
  scores are equal; it is deprecated in favour of `ZRANGE ... BYLEX` since 6.2
  ([ZRANGEBYLEX][redis-zrangebylex], [ZRANGE][redis-zrange]). The upper bound `p + "\xff"` is safe
  for UTF-8 keys because octet `FF` never appears in UTF-8 ([RFC 3629 §1][rfc3629]).
- **Cost of bulk deletes in PostgreSQL.** A large `DELETE` leaves dead tuples for `VACUUM`;
  dropping or detaching a partition "entirely avoid[s] the VACUUM overhead caused by a bulk
  DELETE" ([PostgreSQL partitioning][pg-partitioning]).
- **Pitfalls.** O(m) work happens on the operator's request; in Redis a big invalidation cannot be
  one atomic step without blocking the server (a Lua script blocks all activity while it runs
  ([Redis Lua scripting][redis-lua])), so it is batched and partially visible; every write
  maintains the extra indexes (write amplification); and eager deletion alone does not stop an
  in-flight fetch from re-inserting a stale response (§3).
- **Space.** One index entry per key per access path, plus one row per (tag, key) for tags.

### 2.2 Lazy invalidation: ban lists checked at lookup

Record the invalidation as a predicate; test each entry against it when it is hit; delete later.

- **Varnish.** "Bans are checked when we hit an object in the cache, but before we deliver it";
  "An object is only checked against newer bans"; bans that only reference `obj.*` can also be
  processed by the background ban lurker; bans older than the oldest object are discarded; rarely
  hit long-TTL objects make bans accumulate and cost CPU; `req.*` bans defeat the lurker because it
  has no request ([Varnish purging guide][varnish-purge]).
- **Cost.** Issuing: O(1) (append). Checking: O(b) for arbitrary predicates (Varnish walks the
  bans newer than the object). **Analysis:** for prefix bans, the check is a membership test of
  the key's prefixes in a map `prefix → highest ban sequence`. Restricting ban prefixes to
  boundaries (end of origin, each `/`, the `?`, the full key) bounds the candidate set to `d`
  values, so the check is O(d) hash lookups (memory, Redis `HMGET`) or O(d log b) index probes
  (SQL `prefix = ANY(...)`), independent of `n` and of `b`.
- **Group and global** become prefix bans: the endpoint's authority, and the empty prefix.
- **Ban lifetime (Analysis).** A ban may be dropped once (a) the lurker has removed every older
  matching entry and (b) no fetch that started before the ban can still store. (b) is bounded by
  the maximum fetch duration, enforced by refusing to store a response whose fetch started longer
  ago than that bound. Varnish's rule (drop bans older than the oldest object) is the other
  sufficient condition, and is what makes long-TTL objects pin bans.
- **Pitfalls.** Check cost on every hit; correctness depends on the check reading a current ban
  set (local copies lag); lurker progress governs memory.
- **Space.** O(b), and `b` is bounded by the invalidation rate times the ban lifetime.

### 2.3 Generation, epoch and version counters per namespace

Fold a per-namespace counter into the key, or store it in the entry; bumping it orphans the whole
namespace in O(1).

- **memcached namespacing.** Keep `namespace:<id>` holding a value folded into every key;
  invalidating the group "simply requires editing that key"; each lookup first reads the namespace
  key (one more round trip); old entries are not deleted but left to LRU; "This works well if the
  invalidations are infrequent"; the page warns it "isn't a perfect algorithm" and recommends
  `add` to avoid races when creating the namespace key
  ([memcached ProgrammingTricks][memcached-ns]).
- **Rails recyclable keys** separate the version from the key so that "no matter how frequently
  Product/1 is touched, it'll still only write to the same cache key": the version is stored in
  the entry and compared at read, a mismatch reading as a miss ([rails/rails#29092][rails-29092]).
  This is the in-entry variant: no orphaned keys, one slot per key.
- **Cost.** Invalidate O(1); lookup O(1) extra read (or O(levels) for nested namespaces); orphaned
  entries reclaimed by expiry, eviction or a sweep.
- **Pitfalls.** Only predeclared namespaces (no arbitrary prefixes); the counter read is an extra
  round trip unless cached locally, and a locally cached counter can serve a just-invalidated
  namespace; orphans occupy space until reclaimed, which matters for SQL where nothing evicts.
- **Relation to bans (Analysis).** A generation counter per namespace is a ban list with exactly
  one ban per namespace, keeping only the latest. Sequenced bans generalize it to any prefix with
  a single global counter.

### 2.4 Ordered keys, tries and radix trees for prefixes

- B-trees give O(log n + m) prefix ranges on sorted keys ([Comer 1979][btree]); Redis sorted sets
  give O(log N + M) lex ranges ([ZRANGEBYLEX][redis-zrangebylex]).
- In memory, radix trees (PATRICIA and successors such as the Adaptive Radix Tree) find all keys
  under a prefix in O(|p| + m) ([Leis et al., ICDE 2013][art]). In Python, a dict plus
  `sortedcontainers.SortedList` for ranges is the pragmatic equivalent
  ([sortedcontainers][sortedcontainers]); it is not a HARP dependency today (`pyproject.toml`).
- **Analysis.** For the *check* side, a trie of bans walked along the key is O(|K|); enumerating
  the `d` boundary prefixes and probing a dict is O(d) and needs no tree. Ordered key structures
  are only needed on the *reclaim* side, and there the full-iteration alternative (SCAN, sequential
  scan) is acceptable because reclamation is off the request path.
- **Pitfall.** Prefix semantics depend on key canonicalization: query-parameter order, percent
  encoding and case must be normalized the same way when keys are built and when prefixes are
  issued, or a prefix ban misses entries (**Analysis**).

### 2.5 Tags and surrogate keys (inverted index)

- **Fastly.** "Surrogate keys are unique identifiers that you assign to groups of content";
  carried in `Surrogate-Key`, tokens up to 1 KB, header up to 16 KB; purging a key purges "all of
  the objects associated with that key" ([Fastly surrogate keys][fastly-sk]).
- **Varnish xkey.** Keys in the `xkey` response header; the module "adds secondary hashes to
  objects, allowing fast purging on all objects with this hash key"; `softpurge` "resets an
  object's TTL but keeps it available for grace mode and conditional requests"; the maintainers
  note "known performance issues, particularly regarding scalability" ([vmod_xkey][xkey]).
- **Cost.** Eager: O(m) through the inverted index, plus O(t) index writes per insert. Lazy
  (**Analysis**): a map `tag → ban sequence`, checked in O(t) per hit, same lifetime rule as §2.2.
- **For HARP.** The endpoint is already a prefix, so tags are only needed for groups that cut
  across URLs (an origin-supplied `Surrogate-Key`, say). They fit the same sequenced-ban check.

## 3. Consistency under concurrency

### 3.1 The stale-set race

"A stale set occurs when a web server sets a value in memcache that does not reflect the latest
value that should be cached. This can occur when concurrent updates to memcache get reordered"
([Nishtala et al., §3.2.1][fb-memcache]). For a proxy cache the interleaving is: fetch F starts
for key K; invalidation I of K (or of a prefix of K) runs and deletes; F completes and stores the
response it got before I. Eager deletion cannot prevent it, because the entry does not exist yet
when I runs.

### 3.2 Known fixes

- **Leases.** On a miss memcached hands out "a 64-bit token bound to the specific key"; the set
  must present it; "Verification can fail if memcached has invalidated the lease token due to
  receiving a delete request for that item"; issuing at most one token per key every 10 seconds
  also tames thundering herds (peak DB rate 17K/s to 1.3K/s in their measurement)
  ([Nishtala et al., §3.2.1][fb-memcache]). Leases descend from Gray and Cheriton
  ([SOSP 1989][leases]).
- **Delete rather than update.** Facebook deletes on write "because deletes are idempotent"
  ([Nishtala et al., §2][fb-memcache]).
- **Timestamps instead of tokens** are cited by the same paper as an alternative
  (Ghandeharizadeh and Yap) ([Nishtala et al., §8][fb-memcache]).
- **Optimistic check-and-set.** Redis `WATCH`/`MULTI`/`EXEC` aborts a transaction if a watched key
  changed ([Redis transactions][redis-tx]); a Lua script gives the same atomicity
  ([Redis Lua scripting][redis-lua]).

### 3.3 Version stamps from a global invalidation counter (Analysis)

Keep one counter `S` per cache store, incremented only by invalidations, and give each ban the
value it produced. Before forwarding a cacheable request, read `S` into `snap`; store the response
with `entry.seq = snap`. An entry is valid for a key K iff `entry.seq >= max{ban.seq : ban matches
K}` (equivalently, no matching ban has `seq > entry.seq`).

- **Correct under the race.** If I is issued after F started, `I.seq > snap`, so F's entry is
  invalid as soon as it is written, whatever the write order. This is the lease idea with the token
  shared by every key under a prefix.
- **A stale read of `S` is safe.** Reading a lower `snap` (a locally cached value) can only make an
  entry look older, so it can only cause a needless miss, never a stale hit. So no extra round
  trip per miss is needed: cache `S` locally and refresh it lazily.
- **Bans must commit in sequence order**, otherwise a fetch can read a committed `S` that is
  higher than a lower-numbered ban still in flight. PostgreSQL: allocate the sequence with
  `UPDATE counter SET value = value + 1 RETURNING value`; the row lock serializes bans until commit
  ([PostgreSQL explicit locking][pg-locking]). A `SEQUENCE` does not give this: `nextval` values
  are not ordered by commit and have gaps ([PostgreSQL sequence functions][pg-seq]). Redis: `INCR`
  and the ban write in one script. Bans are rare, so serializing them is free.
- **Older fetch overwriting a newer entry** (two concurrent fetches, the older finishing last) is
  the other face of the reorder problem; guard the upsert with
  `WHERE (excluded.seq, excluded.date) >= (stored.seq, stored.date)`, `Date` being the RFC's
  tie-breaker for "most recent" ([RFC 9111 §4.1][rfc9111]; [PostgreSQL INSERT ON CONFLICT][pg-insert]).
- **Thundering herd** on a just-invalidated hot key is orthogonal; lease-style "one fetch per key"
  or probabilistic early recomputation ([Vattani et al., VLDB 2015][xfetch]) address it.

## 4. Expiry and eviction

### 4.1 Freshness, retention and removal

**Analysis.** Each entry needs two instants: `fresh_until` (RFC 9111 §4.2.1) and `remove_after`
= min(`fresh_until` + grace for stale use and revalidation, `stored_at` + operator TTL). Lookup
checks both in O(1); background removal only cares about `remove_after`. Varnish's soft purge
does the same split (TTL reset, object kept for grace and conditional requests ([vmod_xkey][xkey])).

### 4.2 Structures

| Structure | Insert / cancel / pop-expired | Notes |
|---|---|---|
| Binary heap with lazy deletion | O(log n) / O(1) mark / O(log n) | Python `heapq` documents "mark the entry as removed and add a new entry" ([heapq notes][heapq]); garbage grows with replacements, so rebuild when it dominates |
| Hashed / hierarchical timing wheel | O(1) / O(1) / O(1) amortized | [Varghese and Lauck, SOSP 1987][timing-wheels]; Caffeine uses one for variable expiration, "a time-aware priority queue that uses hashing and doubly linked lists to perform operations in O(1) time" ([Caffeine design][caffeine]) |
| Write-order queue | O(1) | Caffeine's fixed `expireAfterWrite` ([Caffeine design][caffeine]); valid only when every entry has the same TTL, not true for HTTP |
| SQL index on `remove_after` | O(log n) / O(log n) / O(log n + m) | batched `DELETE` of the oldest rows; or partitions by expiry bucket dropped whole ([PostgreSQL partitioning][pg-partitioning]) |
| Redis native expire | O(1) | passive on access plus active sampling "a few keys at random amongst the set of keys with an expiration" ([Redis EXPIRE][redis-expire]); `expired` events fire when the key is deleted, not when the TTL reaches zero ([keyspace notifications][redis-notif]); per-field `HEXPIRE` since 7.4 ([HEXPIRE][redis-hexpire]) |

### 4.3 Eviction under a size bound

- **Redis** evicts by approximate LRU (random sampling plus a candidate pool, tuned by
  `maxmemory-samples`), approximate LFU (Morris counter with decay), random, or `volatile-ttl`;
  `volatile-*` policies only consider keys with an expire, and behave like `noeviction` if there are
  none ([Redis eviction][redis-eviction]; Morris counter: [Morris 1978][morris]).
- **W-TinyLFU** (window LRU in front of a frequency-filtered main region, frequencies in a 4-bit
  Count-Min sketch at about 8 bytes per entry, eviction in O(1)) gives near-optimal hit ratios
  ([Caffeine design][caffeine]; [Einziger, Friedman, Manes, ACM ToS 2017][tinylfu]).
- **SQL** has no eviction. Exact LRU needs a write per hit; in PostgreSQL updating an indexed column
  disables HOT updates ([PostgreSQL HOT][pg-hot]), so a `last_hit_at` index costs a new index
  entry per hit. **Analysis:** evict by `remove_after` or `stored_at` (FIFO-like, free), or buffer
  hit counts in memory and flush them periodically, the way Caffeine's read buffer is "allowed to
  be lossy" ([Caffeine design][caffeine]).

### 4.4 Interaction with invalidation

- Caffeine marks an entry *retired* when it leaves the hash table, before it leaves the policy
  queues ([Caffeine design][caffeine]): removal from the map is the commit point, queue cleanup is
  deferred. The same split applies to bans (logical invalidation) versus lurker (physical).
- Redis eviction does not touch application indexes, so a sorted set or tag set built beside the
  entries holds dangling members after an eviction; `evicted` events exist but Pub/Sub is "fire and
  forget" ([keyspace notifications][redis-notif]). **Analysis:** avoid secondary indexes in Redis,
  or treat every member as a hint verified on use.
- **Analysis, critical for Redis:** under `allkeys-*` policies Redis may evict the bans hash or the
  counter, which resurrects invalidated entries. Give entries a TTL, keep bans and the counter
  without one, and use a `volatile-*` policy, which never evicts keys without an expire
  ([Redis eviction][redis-eviction]).

## 5. Metadata, bodies and size accounting

- **Split.** Small metadata (key, variant, status, size, instants, seq, body reference) apart from
  the body keeps browsing, lurking and expiry from reading bodies. PostgreSQL already moves values
  wider than about 2 kB out of line (`TOAST_TUPLE_THRESHOLD`) ([PostgreSQL TOAST][pg-toast]), but
  an explicit body table also enables deduplication and separate retention (**Analysis**).
- **Content-addressed bodies (Analysis).** Key the body by a digest of its bytes: identical bodies
  across variants, keys or refreshes are stored once. Reclaim by mark-and-sweep (bodies not
  referenced and older than a grace period, so a body written just before its metadata is not
  swept) rather than a reference count updated on every write. In Redis, set each body's expiry
  with `PEXPIREAT ... GT` to the latest referencing entry's `remove_after`: bodies then outlive
  every reference and expire on their own, with no reference count; `GT` sets the expiry "only when
  the new expiry is greater than the current one" ([Redis EXPIRE][redis-expire]). The cost is that
  an invalidated entry's body lingers until its natural expiry unless the lurker deletes it.
- **Size accounting.** Record `body_size` (and header size) in the metadata at write; keep running
  totals per endpoint updated in the same transaction or script as the write and the delete
  (§6). Redis `MEMORY USAGE` measures a key's real footprint, including overhead, when calibration
  is needed ([MEMORY USAGE][redis-memusage]).

## 6. Statistics without scans

- **Counters on write.** Per endpoint: entries, bytes, hits, misses, invalidations. Redis: `HINCRBY`
  inside the write script, O(1) ([INCR family][redis-incr]); `INFO stats` also exposes global
  `keyspace_hits`, `keyspace_misses`, `evicted_keys`, `expired_keys` ([Redis eviction][redis-eviction]),
  but those count every key, not cache semantics. PostgreSQL: one row per endpoint is a hot row;
  **Analysis:** shard it per instance (`(endpoint, instance_id)` primary key) and sum at read, or
  let a single janitor fold deltas. Approximate row counts are available for free from planner
  statistics ([PostgreSQL wiki, Count estimate][pg-count]).
- **Hit ratio over time.** HARP already records each transaction with its `cached` flag
  (decisions.md, facts), so hit ratio by endpoint and period is an aggregate over the existing
  transactions table rather than a new structure (**Analysis**).
- **Biggest entries.** Exact top-k by an index on `(endpoint, body_size DESC)`: O(log n + k) in SQL;
  a heap or sorted list in memory.
- **Hot keys.** Count-Min sketch: point estimates with additive error εN using O((1/ε) log(1/δ))
  counters, and sketches with the same hash functions merge by addition
  ([Cormode and Muthukrishnan 2005][cms]). Space-Saving tracks top-k with k counters and
  guaranteed error bounds ([Metwally, Agrawal, El Abbadi, ICDT 2005][spacesaving]). **Analysis:** one
  sketch per instance, merged when the dashboard reads, avoids a write per hit in the store.

## 7. Variants (`Vary`)

**Analysis**, from RFC 9111 §4.1 ([RFC 9111][rfc9111]):

- Group variants under the primary key: one record per key holding the latest `Vary` field names,
  and one variant per secondary key `h = digest(normalized values of those fields)`. Lookup: one
  read of the key's record, compute `h`, one read of the variant: O(1) in memory and Redis (one
  hash), O(log n) in SQL (primary key `(key, variant)`).
- If stored responses disagree on `Vary` (it changed at the origin), recompute `h` with each
  variant's own field list before serving; RFC 9111 prefers the most recent response with a valid
  `Vary`.
- Never store `Vary: *` for reuse (it never matches); a variant may still be kept for validation.
- Invalidation (§4.4, bans) targets the primary key and so all variants at once; one Redis hash per
  key makes that a single `DEL`.
- Normalize header values (whitespace, list combining, case where the field is case-insensitive)
  before hashing, otherwise equivalent requests fragment the variant set.

## 8. Comparison

| Option | Invalidate exact / prefix / group / all | Lookup overhead | Race-safe | Space overhead | Fits |
|---|---|---|---|---|---|
| Eager + ordered index | O(log n) / O(log n + m) / O(log n + m) / O(1) truncate | none | no, needs tombstones | index per access path | SQL natively; Redis needs ZSETs |
| Bans, arbitrary predicates (Varnish) | O(1) all | O(b) per hit | yes, if stamped before fetch | O(b) | any |
| **Sequenced prefix bans** | O(1) all | O(d) per hit, same round trip | yes | O(b) | SQL, Redis, memory |
| Namespace generations | n/a / n/a / O(1) / O(1) | one read per level, or local cache | only if stamped | orphans until reclaimed | Redis, memory; weak for SQL |
| Tags, eager | O(m) by tag | none | no | O(t) rows per entry | SQL, Redis |
| Tags, lazy | O(1) | O(t) per hit | yes | O(tags) | any |

## 9. Recommended model: sequenced bans with lazy check and background reclaim

### 9.1 Principle

- Every invalidation (exact key, prefix, endpoint, all, RFC 9111 §4.4) becomes one ban record
  `(seq, kind, prefix, mode, created_at, reclaimed)`, where `kind` is `exact` or `subtree`,
  `mode` is `hard` (miss) or `soft` (must revalidate, keeping validators: RFC 9111 §4.4 allows
  either). Endpoint is `subtree` on the key's origin part, all is `subtree` on the empty prefix.
- Every entry carries `seq`, the store's invalidation counter read before its fetch started.
- An entry under key K is usable iff no ban with `seq > entry.seq` matches K: an `exact` ban equal
  to K, or a `subtree` ban equal to one of K's boundary prefixes `P(K)`.
- Reclamation (the lurker) deletes matching entries in the background, then the ban is dropped
  once reclaimed and older than the maximum fetch duration (writes from fetches older than that
  bound are refused).
- Bans, counter and entries live in the same store, and the ban check runs in the lookup's own
  round trip.

### 9.2 PostgreSQL / SQLite

```sql
CREATE TABLE http_cache_entries (
    key          text COLLATE "C" NOT NULL,   -- SQLite: BINARY (default)
    variant      bytea NOT NULL,              -- digest of normalized Vary values; empty if none
    entry_id     uuid NOT NULL,               -- stable across 304 freshening, new on replacement
    endpoint     text NOT NULL,
    seq          bigint NOT NULL,             -- invalidation counter read before the fetch
    status       smallint NOT NULL,
    vary         text,                        -- field names nominated by this response
    body_digest  bytea NOT NULL REFERENCES http_cache_bodies (digest),
    body_size    integer NOT NULL,
    response_date timestamptz,                -- Date header, tie-breaker for "most recent"
    stored_at    timestamptz NOT NULL,
    fresh_until  timestamptz NOT NULL,
    remove_after timestamptz NOT NULL,
    head         bytea NOT NULL,              -- serialized request/response heads
    PRIMARY KEY (key, variant)                -- also serves prefix ranges (C collation)
);
CREATE INDEX ON http_cache_entries (remove_after);
CREATE INDEX ON http_cache_entries (endpoint, stored_at);
CREATE INDEX ON http_cache_entries (endpoint, body_size DESC);
CREATE UNIQUE INDEX ON http_cache_entries (entry_id);

CREATE TABLE http_cache_bodies (
    digest     bytea PRIMARY KEY,
    data       bytea NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE http_cache_bans (
    seq        bigint PRIMARY KEY,
    kind       text NOT NULL,                 -- 'exact' | 'subtree'
    prefix     text COLLATE "C" NOT NULL,
    mode       text NOT NULL,                 -- 'hard' | 'soft'
    created_at timestamptz NOT NULL,
    created_by text,                          -- audited when an account decided (decision 1)
    reclaimed  boolean NOT NULL DEFAULT false
);
CREATE INDEX ON http_cache_bans (prefix, seq);

CREATE TABLE http_cache_counter (id smallint PRIMARY KEY, value bigint NOT NULL);

CREATE TABLE http_cache_stats (
    endpoint text, instance text,
    entries bigint, bytes bigint, hits bigint, misses bigint,
    PRIMARY KEY (endpoint, instance)
);
```

- **Lookup** (one round trip, O(log n + d log b)):
  `SELECT e.* FROM http_cache_entries e WHERE e.key = :k AND NOT EXISTS (SELECT 1 FROM
  http_cache_bans b WHERE b.seq > e.seq AND ((b.kind = 'subtree' AND b.prefix = ANY(:prefixes)) OR
  (b.kind = 'exact' AND b.prefix = :k)))`, then pick the variant in Python (§7). SQLite: `IN (...)`
  with `d` bound parameters. A soft ban returns the row flagged for revalidation instead of hiding
  it.
- **Snapshot before fetch.** `SELECT value FROM http_cache_counter`, cached per instance for a few
  seconds (safe, §3.3).
- **Insert / replace** (O(log n) per index): body first `INSERT ... ON CONFLICT (digest) DO
  NOTHING`, then entry `INSERT ... ON CONFLICT (key, variant) DO UPDATE ... WHERE (excluded.seq,
  excluded.response_date) >= (http_cache_entries.seq, http_cache_entries.response_date)`
  ([PostgreSQL INSERT][pg-insert]). Refuse the write if the fetch started longer ago than the
  maximum fetch duration. Optionally skip it if a matching ban newer than `snap` already exists
  (saves dead rows; correctness does not depend on it).
- **Invalidate** (O(log b), any scope): in one transaction, `UPDATE http_cache_counter SET value =
  value + 1 RETURNING value`, `INSERT INTO http_cache_bans ...`. Exact-key bans can also delete the
  key's rows in the same transaction, since that is O(v log n).
- **Reclaim** (background, O(log n + m) per ban, batched): `DELETE FROM http_cache_entries WHERE
  (key, variant) IN (SELECT key, variant FROM http_cache_entries WHERE key >= :p AND key < :p_succ
  AND seq < :ban_seq LIMIT 1000 FOR UPDATE SKIP LOCKED)` ([PostgreSQL SELECT locking
  clause][pg-select]); the empty prefix means the whole table, where `TRUNCATE` of entries is
  simpler when no newer entry must survive. Mark `reclaimed`, then drop the ban per §9.1.
- **Expiry** (background): the same batched delete on `remove_after < now()`. Partitioning by
  `remove_after` bucket only if `VACUUM` load shows up at millions of rows
  ([PostgreSQL partitioning][pg-partitioning]).
- **Bodies**: sweep digests not referenced by any entry and older than a grace period.
- **Browse**: keyset pagination over `(endpoint, stored_at)` or `(endpoint, body_size)`, with the
  same `NOT EXISTS` ban predicate so invalidated entries disappear immediately, before reclaim.
- **Stats**: increment `http_cache_stats` for this instance in the write and reclaim transactions;
  hit ratio from the transactions table.

### 9.3 Redis

Key layout (namespace `{ns}`, for example `harp:cache`):

| Key | Type | Content | Expiry |
|---|---|---|---|
| `{ns}:e:<K>` | hash | field `vary`: names; field `v:<h>`: packed metadata (entry_id, seq, status, size, instants, body digest, heads) | `PEXPIREAT` = max variant `remove_after` (`GT`); per field `HPEXPIREAT` on 7.4+ |
| `{ns}:b:<digest>` | string | body | `PEXPIREAT ... GT` to the latest referencing entry |
| `{ns}:bans` | hash | `x:<K>` or `s:<prefix>` → highest ban seq | none |
| `{ns}:banlog` | sorted set | member `seq:kind:mode:prefix`, score seq | none (trimmed by the lurker) |
| `{ns}:seq` | string | invalidation counter | none |
| `{ns}:stats` | hash | `<endpoint>:entries`, `:bytes`, `:hits`, `:misses` | none |

- **Lookup**: one `EVALSHA` with `KEYS = [{ns}:e:<K>, {ns}:bans]`, `ARGV = [variant field,
  'x:'..K, 's:'..p1, ..., 's:'..pd]`: `HGET` the variant, `HMGET` the ban fields, compare seqs,
  return the metadata or nil, `HINCRBY` hit or miss. O(d), atomic ([Redis Lua scripting][redis-lua]).
  Then `GET` the body (or fold it into the script).
- **Insert**: script: re-check bans against `snap`, compare with the stored variant's
  `(seq, date)`, `HSET`, `PEXPIREAT GT`, `HINCRBY` stats. Body `SET` with `PEXPIREAT GT` first.
- **Invalidate**: script: `INCR {ns}:seq`, `HSET {ns}:bans <field> <seq>`, `ZADD {ns}:banlog`.
  O(1).
- **Reclaim**: one cursor pass of `SCAN MATCH {ns}:e:<glob-escaped prefix>*` per batch of pending
  bans (several bans share a pass), deleting variants with `seq <` the matching ban, `UNLINK` when
  empty ([Redis SCAN][redis-scan], [UNLINK][redis-unlink]). O(1) per call, O(N) per pass, off the
  request path; a lex sorted set per endpoint would cut this to O(log N + M) at the price of an
  index write per insert and dangling members after eviction (§4.4), so add it only if
  measurements ask.
- **Expiry and eviction**: native; `maxmemory-policy volatile-lru` or `volatile-lfu` so that bans,
  counter and stats (no TTL) are never evicted ([Redis eviction][redis-eviction]).
- **Browse**: through the derived SQL index of decision 2, not Redis; the index reads the bans
  hash (small) to hide invalidated rows.
- **Cluster** (not a target for one to a few instances): a script may only touch declared keys
  ([Redis Lua scripting][redis-lua]), and keys in different hash slots cannot share a script;
  colocating with a hash tag or replicating the bans hash per slot would be needed
  ([cluster spec][redis-cluster]).

### 9.4 Memory (single process)

- `entries: dict[str, KeyRecord]`, `KeyRecord = {vary: tuple[str, ...], variants: dict[bytes,
  Entry]}`; O(1) lookup.
- `bans: dict[tuple[kind, prefix], int]`, counter `int`; O(d) check, kept for the in-flight race
  even though eager deletion is cheap here.
- Expiry: `heapq` of `(remove_after, key, variant, entry_id)` with lazy deletion
  ([heapq notes][heapq]), rebuilt when stale items dominate.
- Size bound: LRU by `OrderedDict` move-to-end, or W-TinyLFU if hit ratio matters
  ([Caffeine design][caffeine]).
- Reclaim: iterate the dict for subtree bans (in-process `n` is small), or a `SortedList` of keys
  if not ([sortedcontainers][sortedcontainers]).

### 9.5 Linking a transaction to its entry

Record on the transaction `cache_key`, `variant` and `entry_id` (plus `seq`), not only `cached`
and age. `entry_id` is stable across 304 freshening (RFC 9111 §4.3.4 updates the stored response
in place) and new on replacement, so the link either resolves to the exact response served or
reads as "since replaced"; the key alone cannot tell versions or variants apart (**Analysis**).

### 9.6 Cost summary

| Operation | PostgreSQL | Redis | Memory |
|---|---|---|---|
| Lookup with variants and ban check | 1 query, O(log n + d log b) | 1 script, O(d) | O(d) |
| Snapshot | cached, ~0 | cached, ~0 | O(1) |
| Insert / replace | O(log n) × indexes | O(1) | O(log n) heap |
| Invalidate exact / prefix / endpoint / all | O(log b) | O(1) | O(1) |
| Reclaim (background) | O(log n + m) per ban | O(N) per SCAN pass | O(n) or O(log n + m) |
| Expire (background) | O(log n + m) | native | O(log n) per item |
| Browse page | O(log n + page) | via SQL index | O(n log n) sort, or sorted lists |
| Stats | O(endpoints × instances) | O(1) `HGETALL` | O(1) |
| Top-k by size | O(log n + k) | via SQL index | heap O(n log k) |

## 10. Alternative: eager range deletion with write-time tombstones

For a team that prefers zero work on the hit path:

- Lookup reads only the entry: no ban check, so O(log n) SQL, O(1) Redis.
- Invalidation deletes synchronously: one `DELETE` on the key range in SQL (atomic,
  O(log n + m)); `TRUNCATE` for all; in Redis a per-endpoint lex sorted set gives the members
  (`ZRANGE BYLEX`), deleted in batches (non-atomic, partially visible while it runs).
- The stale-set race is still handled by short-lived tombstones: each invalidation also writes a
  ban `(seq, prefix)` that lives only for the maximum fetch duration and is checked **at write
  time only** against the entry's `snap` (§3.3).
- "All" and "endpoint" can be O(1) with namespace generations folded into the Redis key
  (`{ns}:<epoch>:<endpoint-gen>:e:<K>`) ([memcached ProgrammingTricks][memcached-ns]), orphans left
  to TTL and eviction; in SQL the generation sits in a column and orphans are deleted by the
  janitor.
- Trade-off: invalidation latency grows with `m` (millions of rows for an endpoint purge),
  PostgreSQL pays `VACUUM` for each bulk delete ([PostgreSQL partitioning][pg-partitioning]), Redis
  needs index maintenance on every write and suffers dangling index members after eviction, and
  soft invalidation (revalidate instead of delete) is not expressible without reintroducing a
  lookup-time check.

## 11. Open points for the spike

- Key canonicalization (query order, encoding, case) must be fixed before prefixes mean anything
  (§2.4).
- Maximum fetch duration: the proxy's client timeout is the natural bound (`harp_apps/http_client/settings.py`
  carries a `timeout` argument); a response whose fetch exceeded it is not stored.
- Whether the derived SQL index (decision 2) also serves as the PostgreSQL store itself when the
  cache backend is SQL, to avoid two tables holding the same metadata.
- Whether soft bans (revalidate) are the default for operator invalidations, hard bans for RFC 9111
  §4.4 unsafe-method invalidations.

## Sources

- [rfc9111]: R. Fielding, M. Nottingham, J. Reschke, *HTTP Caching*, RFC 9111, 2022. https://www.rfc-editor.org/rfc/rfc9111
- [rfc3629]: F. Yergeau, *UTF-8, a transformation format of ISO 10646*, RFC 3629, 2003. https://www.rfc-editor.org/rfc/rfc3629
- [fb-memcache]: R. Nishtala et al., *Scaling Memcache at Facebook*, NSDI 2013. https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala (PDF: https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf)
- [leases]: C. Gray, D. Cheriton, *Leases: an efficient fault-tolerant mechanism for distributed file cache consistency*, SOSP 1989. https://doi.org/10.1145/74851.74870
- [varnish-purge]: Varnish Cache, *Purging and banning*. https://www.varnish.org/docs/users-guide/purging/
- [xkey]: Varnish modules, *vmod_xkey*. https://github.com/varnish/varnish-modules/blob/master/src/vmod_xkey.vcc
- [fastly-sk]: Fastly, *Working with surrogate keys*. https://www.fastly.com/documentation/guides/full-site-delivery/purging/working-with-surrogate-keys/
- [memcached-ns]: memcached wiki, *Programming tricks: namespacing*. https://github.com/memcached/memcached/wiki/ProgrammingTricks#namespacing
- [rails-29092]: rails/rails pull request 29092, *Recyclable cache keys*. https://github.com/rails/rails/pull/29092
- [caffeine]: B. Manes, *Caffeine design*. https://github.com/ben-manes/caffeine/wiki/Design
- [tinylfu]: G. Einziger, R. Friedman, B. Manes, *TinyLFU: A Highly Efficient Cache Admission Policy*, ACM Transactions on Storage 13(4), 2017. https://doi.org/10.1145/3149371 (preprint https://arxiv.org/abs/1512.00727)
- [timing-wheels]: G. Varghese, T. Lauck, *Hashed and hierarchical timing wheels*, SOSP 1987. https://doi.org/10.1145/41457.37504
- [cms]: G. Cormode, S. Muthukrishnan, *An improved data stream summary: the count-min sketch and its applications*, Journal of Algorithms 55(1), 2005. https://doi.org/10.1016/j.jalgor.2003.12.001
- [spacesaving]: A. Metwally, D. Agrawal, A. El Abbadi, *Efficient Computation of Frequent and Top-k Elements in Data Streams*, ICDT 2005, LNCS 3363. https://doi.org/10.1007/978-3-540-30570-5_27
- [morris]: R. Morris, *Counting large numbers of events in small registers*, CACM 21(10), 1978. https://doi.org/10.1145/359619.359627
- [xfetch]: A. Vattani, F. Chierichetti, K. Lowenstein, *Optimal probabilistic cache stampede prevention*, PVLDB 8(8), 2015. https://doi.org/10.14778/2757807.2757813
- [art]: V. Leis, A. Kemper, T. Neumann, *The adaptive radix tree: ARTful indexing for main-memory databases*, ICDE 2013. https://doi.org/10.1109/ICDE.2013.6544812
- [btree]: D. Comer, *The Ubiquitous B-Tree*, ACM Computing Surveys 11(2), 1979. https://doi.org/10.1145/356770.356776
- [pg-opclass]: PostgreSQL, *Operator classes and operator families*. https://www.postgresql.org/docs/current/indexes-opclass.html
- [pg-partitioning]: PostgreSQL, *Table partitioning*. https://www.postgresql.org/docs/current/ddl-partitioning.html
- [pg-toast]: PostgreSQL, *TOAST*. https://www.postgresql.org/docs/current/storage-toast.html
- [pg-hot]: PostgreSQL, *Heap-only tuples*. https://www.postgresql.org/docs/current/storage-hot.html
- [pg-insert]: PostgreSQL, *INSERT, ON CONFLICT clause*. https://www.postgresql.org/docs/current/sql-insert.html
- [pg-select]: PostgreSQL, *SELECT, the locking clause (SKIP LOCKED)*. https://www.postgresql.org/docs/current/sql-select.html
- [pg-locking]: PostgreSQL, *Explicit locking (row-level locks)*. https://www.postgresql.org/docs/current/explicit-locking.html
- [pg-seq]: PostgreSQL, *Sequence manipulation functions*. https://www.postgresql.org/docs/current/functions-sequence.html
- [pg-count]: PostgreSQL wiki, *Count estimate*. https://wiki.postgresql.org/wiki/Count_estimate
- [sqlite-like]: SQLite, *The SQLite query optimizer overview, §5 the LIKE optimization*. https://www.sqlite.org/optoverview.html
- [redis-eviction]: Redis, *Key eviction*. https://redis.io/docs/latest/develop/reference/eviction/
- [redis-expire]: Redis, *EXPIRE* (appendix: how Redis expires keys). https://redis.io/docs/latest/commands/expire/
- [redis-hexpire]: Redis, *HEXPIRE*. https://redis.io/docs/latest/commands/hexpire/
- [redis-notif]: Redis, *Keyspace notifications* (timing of expired events). https://redis.io/docs/latest/develop/pubsub/keyspace-notifications/
- [redis-scan]: Redis, *SCAN* (scan guarantees). https://redis.io/docs/latest/commands/scan/
- [redis-zrangebylex]: Redis, *ZRANGEBYLEX*. https://redis.io/docs/latest/commands/zrangebylex/
- [redis-zrange]: Redis, *ZRANGE*. https://redis.io/docs/latest/commands/zrange/
- [redis-lua]: Redis, *Scripting with Lua*. https://redis.io/docs/latest/develop/programmability/eval-intro/
- [redis-tx]: Redis, *Transactions*. https://redis.io/docs/latest/develop/using-commands/transactions/
- [redis-unlink]: Redis, *UNLINK*. https://redis.io/docs/latest/commands/unlink/
- [redis-memusage]: Redis, *MEMORY USAGE*. https://redis.io/docs/latest/commands/memory-usage/
- [redis-incr]: Redis, *INCR*. https://redis.io/docs/latest/commands/incr/
- [redis-cluster]: Redis, *Cluster specification*. https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
- [heapq]: Python, *heapq, priority queue implementation notes*. https://docs.python.org/3/library/heapq.html
- [sortedcontainers]: G. Jenks, *Sorted Containers*. https://grantjenks.com/docs/sortedcontainers/

[rfc9111]: https://www.rfc-editor.org/rfc/rfc9111
[rfc3629]: https://www.rfc-editor.org/rfc/rfc3629
[fb-memcache]: https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala
[leases]: https://doi.org/10.1145/74851.74870
[varnish-purge]: https://www.varnish.org/docs/users-guide/purging/
[xkey]: https://github.com/varnish/varnish-modules/blob/master/src/vmod_xkey.vcc
[fastly-sk]: https://www.fastly.com/documentation/guides/full-site-delivery/purging/working-with-surrogate-keys/
[memcached-ns]: https://github.com/memcached/memcached/wiki/ProgrammingTricks#namespacing
[rails-29092]: https://github.com/rails/rails/pull/29092
[caffeine]: https://github.com/ben-manes/caffeine/wiki/Design
[tinylfu]: https://doi.org/10.1145/3149371
[timing-wheels]: https://doi.org/10.1145/41457.37504
[cms]: https://doi.org/10.1016/j.jalgor.2003.12.001
[spacesaving]: https://doi.org/10.1007/978-3-540-30570-5_27
[morris]: https://doi.org/10.1145/359619.359627
[xfetch]: https://doi.org/10.14778/2757807.2757813
[art]: https://doi.org/10.1109/ICDE.2013.6544812
[btree]: https://doi.org/10.1145/356770.356776
[pg-opclass]: https://www.postgresql.org/docs/current/indexes-opclass.html
[pg-partitioning]: https://www.postgresql.org/docs/current/ddl-partitioning.html
[pg-toast]: https://www.postgresql.org/docs/current/storage-toast.html
[pg-hot]: https://www.postgresql.org/docs/current/storage-hot.html
[pg-insert]: https://www.postgresql.org/docs/current/sql-insert.html
[pg-select]: https://www.postgresql.org/docs/current/sql-select.html
[pg-locking]: https://www.postgresql.org/docs/current/explicit-locking.html
[pg-seq]: https://www.postgresql.org/docs/current/functions-sequence.html
[pg-count]: https://wiki.postgresql.org/wiki/Count_estimate
[sqlite-like]: https://www.sqlite.org/optoverview.html
[redis-eviction]: https://redis.io/docs/latest/develop/reference/eviction/
[redis-expire]: https://redis.io/docs/latest/commands/expire/
[redis-hexpire]: https://redis.io/docs/latest/commands/hexpire/
[redis-notif]: https://redis.io/docs/latest/develop/pubsub/keyspace-notifications/
[redis-scan]: https://redis.io/docs/latest/commands/scan/
[redis-zrangebylex]: https://redis.io/docs/latest/commands/zrangebylex/
[redis-zrange]: https://redis.io/docs/latest/commands/zrange/
[redis-lua]: https://redis.io/docs/latest/develop/programmability/eval-intro/
[redis-tx]: https://redis.io/docs/latest/develop/using-commands/transactions/
[redis-unlink]: https://redis.io/docs/latest/commands/unlink/
[redis-memusage]: https://redis.io/docs/latest/commands/memory-usage/
[redis-incr]: https://redis.io/docs/latest/commands/incr/
[redis-cluster]: https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
[heapq]: https://docs.python.org/3/library/heapq.html
[sortedcontainers]: https://grantjenks.com/docs/sortedcontainers/
