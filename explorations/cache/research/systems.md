# How mature caches model entries, variants and invalidation

Research spike for explore/cache, decision 3 (`explorations/cache/decisions.md`). Collected 2026-10-25.
Primary sources only: vendor docs, maintainer blog posts, papers, and source code pinned to a tag or
commit. Line anchors in source links were checked against raw copies of the pinned files. Statements
marked *(inference)* are my reasoning from the cited material, not a claim of the source.

Pins: Varnish `varnish-7.6.0`, varnish-modules `0.25.0`, ATS `10.1.5`, nginx `release-1.27.3`, Squid
`SQUID_6_9`, Souin `v1.7.9` (storages `81250fe`), Envoy `v1.40.1`, Pingora `0.9.0` (`702f690`), hishel
`1.4.0` (`e10e023`), HARP `d8cc4be`. Varnish 7.6 docs: `varnish-cache.org/docs/7.6` now redirects to
unversioned pages, and the versioned copy is served at `vinyl-cache.org/docs/7.6`, which is what I cite.

## Contents

1. [HARP today](#1-harp-today)
2. [Systems](#2-systems)
3. [Comparison](#3-comparison)
4. [Patterns that win, per operation](#4-patterns-that-win-per-operation)
5. [Candidate models for HARP](#5-candidate-models-for-harp)
6. [Recommendation](#6-recommendation)
7. [Gaps and unverified points](#7-gaps-and-unverified-points)

---

## 1. HARP today

Base: `https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/`, called `H/` below.

- **One `cache/meta` blob per cache key**, holding a YAML list of variants, at most
  `MAX_VARIANTS_PER_KEY = 8` ([H/harp_apps/http_cache/storages.py#L41-L42](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L41-L42),
  [H/harp_apps/http_cache/adapters.py#L149-L156](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/adapters.py#L149-L156)).
  Each variant is identified by its `selecting` headers (the request values of the `Vary` names)
  ([adapters.py#L69-L80](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/adapters.py#L69-L80)).
  It points at separate, content-addressed header and body blobs
  ([adapters.py#L185-L260](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/adapters.py#L185-L260)).
  Writing a variant is a read-modify-write of the whole meta blob under a per-process `asyncio.Lock`
  ([storages.py#L157-L162](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L157-L162),
  [#L283-L299](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L283-L299)).
- **Expiry** is a storage TTL counted from `stored_at`. A background sweep enumerates every
  `cache/meta` blob and decodes each one
  ([storages.py#L227-L255](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L227-L255)).
  On Redis, that enumeration is a `SCAN` over the whole keyspace plus a `GETRANGE` per key to read the
  content type
  ([H/harp_apps/storage/services/blob_storages/redis.py#L83-L117](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/storage/services/blob_storages/redis.py#L83-L117)).
  On SQL, it is a keyset scan of the `blobs` table filtered on `content_type`
  ([H/harp_apps/storage/services/blob_storages/sql.py#L143-L165](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/storage/services/blob_storages/sql.py#L143-L165)).
- **Invalidation and the fill race.** `invalidate(key)` drops every variant of the key. It also
  bumps an in-memory stamp, and an in-memory log of 8192 invalidated keys refuses responses whose
  request set out before the invalidation
  ([storages.py#L111-L183](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L111-L183)).
  This is the same idea as Facebook's leases (§2.12). It lives in one process, so a second instance
  on the same store does not see it *(inference)*.
- **Entry ids.** hishel addresses entries by UUID, and HARP keeps a bounded map from id to key
  ([storages.py#L98-L109](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/http_cache/storages.py#L98-L109)).
- **Transaction link.** A transaction records only `cached` and the age, not which entry served it
  ([H/harp_apps/proxy/controllers.py#L337-L343](https://github.com/msqd/harp/blob/d8cc4be57eb1fb486d141b566186a023917812b8/harp_apps/proxy/controllers.py#L337-L343)).

Consequence: listing, statistics, invalidation by prefix or endpoint, and invalidation of
everything are all O(N decoded blobs). Only exact-key lookup and exact-key invalidation are cheap.

---

## 2. Systems

### 2.1 Varnish Cache 7.6

**Key.** A SHA256 digest of whatever `vcl_hash` feeds to `hash_data()`. By default that is the URL,
then the Host header or the server IP
([cache_hash.c#L191-L202](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_hash.c#L191-L202),
[builtin.vcl#L119-L131](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/builtin.vcl#L119-L131)).
The digest is indexed by a critbit tree
([mgt_main.c#L624](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/mgt/mgt_main.c#L624)).
The key carries no structure, so the index cannot answer "everything under host X" *(inference)*.

**Objects and variants.** There is one `objhead` per digest, holding a list of `objcore`s plus a
waiting list of requests parked on a busy object
([cache_objhead.h#L35-L57](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_objhead.h#L35-L57)).
An `objcore` carries a `hits` counter, `t_origin`, `ttl`, `grace` and `keep`, an expiry heap index,
and `struct ban *ban`, the newest ban it has been checked against
([cache.h#L334-L363](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache.h#L334-L363)).
Vary is not part of the hash. Variants are sibling objcores on one objhead, and each carries an
`OA_VARY` match string of (header, value) pairs
([cache_vary.c#L30-L57](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_vary.c#L30-L57)).
`HSH_Lookup` walks that list linearly. For each object it runs the ban check, then `VRY_Match`
([cache_hash.c#L423-L496](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_hash.c#L423-L496)).
A lookup therefore costs O(1) for the digest plus O(V) over the variants.

**PURGE.** `HSH_Purge` acts on one objhead, so on all its variants at once. It skips `OC_F_BUSY`
objects (fetches in flight), and it either kills objects or, for a soft purge, reduces their TTL
([cache_hash.c#L671-L778](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_hash.c#L671-L778);
[users-guide/purging](https://vinyl-cache.org/docs/7.6/users-guide/purging.html)). A soft purge can
only shorten a lifetime
([vmod_purge.vcc#L87-L142](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/vmod/vmod_purge.vcc#L87-L142)).

**BAN: a lazy predicate log.**
- `BAN_Commit` pushes the ban onto a global list, newest first, in O(1)
  ([cache_ban_build.c#L319-L401](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban_build.c#L319-L401)).
  With `ban_dups` on, it also scans the list for duplicates, which costs O(B)
  ([#L384-L394](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban_build.c#L384-L394)).
- An object is linked to the newest ban when it becomes non-busy
  ([cache_ban.c#L249-L261](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban.c#L249-L261)).
  At lookup it is tested only against bans newer than its checkpoint
  ([cache_ban.c#L627-L713](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban.c#L627-L713)):
  "An object is only checked against newer bans"
  ([purging](https://vinyl-cache.org/docs/7.6/users-guide/purging.html)).
- Bans may test `req.url` and `req.http.*`, or `obj.status`, `obj.http.*`, `obj.ttl` and so on
  ([ban_vars.h#L36-L59](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/include/tbl/ban_vars.h#L36-L59)).
- **The ban lurker** evaluates bans in the background, without a request. A `req.*` ban therefore
  stops it, acting as a barrier
  ([cache_ban_lurker.c#L290-L299](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban_lurker.c#L290-L299),
  [#L339-L410](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban_lurker.c#L339-L410)).
  The docs recommend copying the URL into a stored header and banning on `obj.http.url`
  ([purging](https://vinyl-cache.org/docs/7.6/users-guide/purging.html)).
- The lurker waits `ban_lurker_age` (60 s), then works in paced batches
  ([params.h#L183-L224](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/include/tbl/params.h#L183-L224)).
  A ban is freed once no object references it
  ([cache_ban_lurker.c#L58-L99](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_ban_lurker.c#L58-L99)).
  Long-TTL, rarely read objects let bans accumulate, and the experimental `ban_cutoff` expunges
  everything past the N-th ban to bound lookup cost
  ([params.h#L153-L181](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/include/tbl/params.h#L153-L181)).
- Cost: issuing is O(1); each lookup pays O(newer bans); the background work is O(objects × old bans).

**Fill race.** PURGE, bans and xkey all skip busy objects. A ban committed while a fetch is running
is older than the object's checkpoint once it is unbusied, so it is never tested against it *(inference
from the code above)*. The docs state the general rule: "A ban will only work on objects already in the
cache, it does not prevent new content from entering the cache"
([purging](https://vinyl-cache.org/docs/7.6/users-guide/purging.html)). Varnish accepts the race.

**xkey: an eager tag index.** Two red-black trees behind one global mutex: tag hash → objects, and
object → its tag links
([vmod_xkey.c#L44-L99](https://github.com/varnish/varnish-modules/blob/0.25.0/src/vmod_xkey.c#L44-L99)).
The index is maintained on the `OEV_INSERT` and `OEV_EXPIRE` events
([#L565-L606](https://github.com/varnish/varnish-modules/blob/0.25.0/src/vmod_xkey.c#L565-L606)).
A purge costs O(log K + m) and skips busy objects
([#L507-L563](https://github.com/varnish/varnish-modules/blob/0.25.0/src/vmod_xkey.c#L507-L563)).
Varnish Enterprise ykey adds `add_tree_keys()`, one key per path segment, which turns a URL-prefix
purge into a key purge. It also adds per-key aggregates (`count`, `bodylen`, `hits`) through
`stat_int`/`stat_real`
([ykey docs](https://docs.varnish-software.com/varnish-enterprise/vmods/ykey/)).

**Listing and the link to a transaction.** The CLI has no object listing
([varnish-cli](https://vinyl-cache.org/docs/7.6/reference/varnish-cli.html)). A hit is stamped
`X-Varnish: <req vxid> <obj vxid>`, naming the object
([cache_req_fsm.c#L155-L159](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_req_fsm.c#L155-L159)).

**Expiry** is a binary heap with O(log N) operations
([cache_expire.c#L344-L389](https://github.com/varnishcache/varnish-cache/blob/varnish-7.6.0/bin/varnishd/cache/cache_expire.c#L344-L389)).
**Persistence** forces bans to persist next to the objects, kept "painfully in sync"
([phk/persistent](https://vinyl-cache.org/docs/7.6/phk/persistent.html)). MSE4 removes, at boot, any
object whose ban is missing from the journal
([MSE4 persisted](https://docs.varnish-software.com/varnish-enterprise/features/mse_4/persisted/)).

**Multi-node.** None in open source. Enterprise Broadcaster fans the same PURGE or BAN request out to
every node ([broadcaster](https://docs.varnish-software.com/varnish-broadcaster/)).

### 2.2 Apache Traffic Server 10.1

**Directory.** Each stripe has a fixed-size in-RAM hash table of 10-byte entries, keyed by a 128-bit
cache ID (MD5 of the URL by default)
([architecture.en.rst#L151-L178](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L151-L178),
[P_CacheDir.h#L49-L57](https://github.com/apache/trafficserver/blob/10.1.5/src/iocore/cache/P_CacheDir.h#L49-L57),
[CryptoHash.cc#L33-L37](https://github.com/apache/trafficserver/blob/10.1.5/src/tscore/CryptoHash.cc#L33-L37)).
"The cache key is not stored explicitly and therefore cannot be reliably retrieved"
([#L188-L193](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L188-L193)).

**Storage.** Content goes to a circular buffer. The write cursor overwrites the oldest data, and that
is the eviction. Removing an object only changes the directory: "no disk I/O"
([#L323-L348](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L323-L348),
[#L480-L501](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L480-L501)).

**Vary (alternates).** "All metadata for all alternates is stored in the first fragment", as a vector
holding each alternate's headers and the key of its content
([#L369-L413](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L369-L413)).
Changing an alternate rewrites that first Doc: "The only contention is the first Doc"
([#L912-L934](https://github.com/apache/trafficserver/blob/10.1.5/doc/developer-guide/cache-architecture/architecture.en.rst#L912-L934)).
`max_alts` defaults to 5
([records.yaml.en.rst#L2658-L2672](https://github.com/apache/trafficserver/blob/10.1.5/doc/admin-guide/files/records.yaml.en.rst#L2658-L2672)).
This is HARP's current layout.

**PURGE** costs O(1) in the directory plus one verification read, and drops all alternates
([CacheVC.cc#L557-L637](https://github.com/apache/trafficserver/blob/10.1.5/src/iocore/cache/CacheVC.cc#L557-L637)).
If a writer is open, the purge sets `dont_update_directory` on it
([#L573-L584](https://github.com/apache/trafficserver/blob/10.1.5/src/iocore/cache/CacheVC.cc#L573-L584),
[CacheWrite.cc#L338](https://github.com/apache/trafficserver/blob/10.1.5/src/iocore/cache/CacheWrite.cc#L338)),
so an in-flight fill never becomes visible *(inference from both lines)*.

**regex_revalidate (lazy prefix or pattern).** Each rule is `<regex> <expiry> [MISS|STALE]` and gets
the time it was loaded as its epoch
([regex_revalidate.en.rst#L62-L133](https://github.com/apache/trafficserver/blob/10.1.5/doc/admin-guide/plugins/regex_revalidate.en.rst#L62-L133)).
On a fresh hit, it matches every rule whose epoch is at or after the cached `Date`
([regex_revalidate.cc#L674-L726](https://github.com/apache/trafficserver/blob/10.1.5/plugins/regex_revalidate/regex_revalidate.cc#L674-L726)).
Recording a rule is O(1); each hit costs O(rules); rules must expire. Comparing against `Date` misfires
behind a caching parent
([#L129-L133](https://github.com/apache/trafficserver/blob/10.1.5/doc/admin-guide/plugins/regex_revalidate.en.rst#L129-L133)).

**Cache generation (namespace versioning).** `proxy.config.http.cache.generation` is "combined with the
cache key at cache lookup time. Changing this value has the effect of an instantaneous, zero-cost cache
purge", either globally or per remap rule
([records.yaml.en.rst#L2353-L2363](https://github.com/apache/trafficserver/blob/10.1.5/doc/admin-guide/files/records.yaml.en.rst#L2353-L2363),
[URL.cc#L1860-L1863](https://github.com/apache/trafficserver/blob/10.1.5/src/proxy/hdrs/URL.cc#L1860-L1863)).
A fill started under the old generation lands under a key nobody looks up, so it is race-safe for free
*(inference)*.

**Listing and statistics.** Listing needs a stripe scan with disk reads
([traffic_server.en.rst#L61-L64](https://github.com/apache/trafficserver/blob/10.1.5/doc/appendices/command-line/traffic_server.en.rst#L61-L64)).

**Multi-node.** None: a PURGE affects "a specific Traffic Server cache"
([storage/index.en.rst#L309-L313](https://github.com/apache/trafficserver/blob/10.1.5/doc/admin-guide/storage/index.en.rst#L309-L313)).

### 2.3 nginx proxy_cache 1.27

**Index.** File name = MD5 of `proxy_cache_key`; the full key text is written into the file header
([proxy_cache_path](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_path),
[ngx_http_file_cache.c#L79](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L79)).
The keys zone in shared memory is an rbtree plus an LRU queue of nodes, about 8,000 keys per MB
([ngx_http_cache.h#L39-L62](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_cache.h#L39-L62),
[ngx_http_file_cache.c#L1029-L1071](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L1029-L1071)).
A node holds the hash, `uses`, `expire`, `valid_sec`, `fs_size` and flag bits. It holds no URL.

**Maintenance.** The cache manager evicts entries left unused for `inactive`, and enforces `max_size`
by LRU in bounded iterations
([#L1860-L1935](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L1860-L1935),
[#L2022-L2105](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L2022-L2105)).
At startup the loader walks the directory tree to rebuild the zone
([#L2109-L2150](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L2109-L2150)).

**Vary.** A variant is stored at MD5(key ‖ the request's Vary values)
([#L1117-L1163](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L1117-L1163)).
The main file holds one variant and links to no other, so a purge by key misses the rest. The
maintained purge fork walks the directory to purge every variant
([ARCHITECTURE.md#L47](https://github.com/nginx-modules/ngx_cache_purge/blob/5c2b7d909fe4c31c06deacef9be0dce65e30ceef/docs/ARCHITECTURE.md?plain=1#L47)).

**Purge.**
- NGINX Plus wildcard `key*` is lazy. Entries "remain on the disk until they are deleted for either
  inactivity, or processed by the cache purger, or a client attempts to access them"
  ([proxy_cache_purge](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_purge)).
  The purger "permanently iterates through all cache entries"
  ([proxy_cache_path](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_path)).
- FRiCKLE `ngx_cache_purge` purges exact keys only
  ([ngx_cache_purge_module.c#L1442-L1500](https://github.com/FRiCKLE/ngx_cache_purge/blob/331fe43e8d9a3d1fa5e0c9fec7d3201d431a9177/ngx_cache_purge_module.c#L1442-L1500)).
- The nginx-modules fork adds generation keys: "Advancing that version makes older entries unreachable,
  including late writes using an old key". It deliberately keeps no file-to-tag index
  ([ARCHITECTURE.md#L19](https://github.com/nginx-modules/ngx_cache_purge/blob/5c2b7d909fe4c31c06deacef9be0dce65e30ceef/docs/ARCHITECTURE.md?plain=1#L19),
  [#L31-L33](https://github.com/nginx-modules/ngx_cache_purge/blob/5c2b7d909fe4c31c06deacef9be0dce65e30ceef/docs/ARCHITECTURE.md?plain=1#L31-L33)).

**Fill race.** Core nginx sets `exists = 1` unconditionally when it commits a fill, so a fetch begun
before a purge lands after it
([#L1418-L1489](https://github.com/nginx/nginx/blob/release-1.27.3/src/http/ngx_http_file_cache.c#L1418-L1489)).

**Statistics.** The Plus API exposes per-cache hit, miss and bytes counters
([api module](https://nginx.org/en/docs/http/ngx_http_api_module.html)). Per request,
`$upstream_cache_status` gives the status
([upstream module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#var_upstream_cache_status)).

### 2.4 Squid 6.9

**Index.** Store key = MD5(method ‖ URL [‖ vary mark]), held in a global hash table of `StoreEntry`
records without the URL
([store_key_md5.cc#L94-L136](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/store_key_md5.cc#L94-L136),
[Store.h#L221-L244](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/Store.h#L221-L244)).

**Vary.** A **marker object** at the base key records the `Vary` header. The variant then lives at
MD5(URL ‖ mark), so a hit takes two lookups
([store.cc#L646-L720](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/store.cc#L646-L720),
[client_side.cc#L3468-L3530](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/client_side.cc#L3468-L3530)).
PURGE removes only the variant matching the purging request's own headers. The code says: "We probably
cannot purge Vary-affected responses because their MD5 keys depend on vary headers"
([client_side_reply.cc#L855-L978](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/client_side_reply.cc#L855-L978)).

**Fill race.** A purge of a locked entry switches it to a private key with `RELEASE_REQUEST`, and
`makePublic` refuses such an entry, so a fill in flight never becomes visible
([store.cc#L1133-L1157](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/store.cc#L1133-L1157),
[#L166-L184](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/store.cc#L166-L184)).

**Bulk invalidation.** There is no prefix, host or "all" purge *(inference: none found; keys are
opaque)*.

**Listing and statistics.** The cachemgr `objects` report is a full scan
([stat.cc#L368-L415](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/stat.cc#L368-L415)).
Hit ratios come from rolling counters
([stat.cc#L476-L480](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/stat.cc#L476-L480)).

**Multi-node.** HTCP CLR is eager, per-URL fan-out
([htcp.cc#L1017-L1052](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/htcp.cc#L1017-L1052)).
Cache digests are Bloom filters that do not support deletion
([CacheDigest.cc#L139-L145](https://github.com/squid-cache/squid/blob/SQUID_6_9/src/CacheDigest.cc#L139-L145)).

### 2.5 Fastly

**Surrogate keys.** Keys are space-separated, at most 1 KB each and 16 KB per header. Fastly builds "a
mapping from each key to the cached content"
([working with surrogate keys](https://www.fastly.com/documentation/guides/full-site-delivery/purging/working-with-surrogate-keys/)).
The 2013 implementation: a crit-bit tree of keys whose leaves are red-black trees of objcore
pointers, and back-pointers from each object to its keys so that expiry unlinks it. Add and remove
cost O(k); a hash table was rejected because resize pauses could "miss" purges
([Surrogate Keys Part 2](https://www.fastly.com/blog/surrogate-keys-part-2)).

**Purge types.** URL purge, key purge and purge-all. A soft purge "marks it as stale" and exists only
for URL and key purges; "Purge all is a hard purge". Each key counts as one purge whatever the number
of tagged objects
([purging concepts](https://www.fastly.com/documentation/guides/concepts/edge-state/cache/purging/),
[purge API](https://www.fastly.com/documentation/reference/api/purging/)).

**Vary.** A secondary key under the same cache key, with a soft limit of 50 and a hard limit of 75
variants. "Varied responses with the same cache key are all wiped with a single purge for that URL"
([Getting the most out of Vary](https://www.fastly.com/blog/getting-most-out-vary-fastly)).

**Multi-node.** UDP broadcast, then gossip repair (Bimodal Multicast) with eventual delivery
([Building a Fast and Reliable Purging System](https://www.fastly.com/blog/building-fast-and-reliable-purging-system)).
Mean global purge time is under 150 ms
([Instant Purge under 150ms](https://www.fastly.com/blog/fastly-instant-purge-under-150ms-for-over-a-decade)).

The fill-vs-purge race is not published.

### 2.6 Cloudflare (and Pingora)

**Purge scopes.** URL, hostname, tag, prefix and everything. Prefix: at most 31 path separators, and
no query string
([purge cache](https://developers.cloudflare.com/cache/how-to/purge-cache/),
[purge by prefix](https://developers.cloudflare.com/cache/how-to/purge-cache/purge_by_prefix/),
[purge by tags](https://developers.cloudflare.com/cache/how-to/purge-cache/purge-by-tags/)).
"Invalidate everything" revalidates instead of deleting
([purge everything](https://developers.cloudflare.com/cache/how-to/purge-cache/purge-everything/)).

**From lazy to indexed purge**
([Instant Purge, 2024-09-24](https://blog.cloudflare.com/instant-purge/)):
- **Before.** On a hit, the cache compared recent purge timestamps with the file's insertion time and
  "pretend[ed] we didn't find the file". Nothing was deleted, because finding the tagged files would
  mean looking "at every file in every cache disk". Purged-but-retained files cut into disk space.
- **After.** CacheDB, a Rust service on RocksDB on each machine, indexes "hostnames, cache-tags, and
  URLs". A local queue buffers purges, and a background process deletes the matching files through the
  indices. On a hit, CacheDB "does a quick scan of its local queue to see if there are any pending
  purge operations". P50 went from 1,570 ms to 149 ms.
- Active purge cut storage needs by 10x
  ([Instant Purge for all](https://blog.cloudflare.com/instant-purge-for-all/)).

**Vary.** In 2026 Vary became configurable, with listed headers entering the cache key. "Purging a URL
purges all cached versions for that URL"
([Vary concepts](https://developers.cloudflare.com/cache/concepts/vary/),
[changelog 2026-07-02](https://developers.cloudflare.com/changelog/post/2026-07-02-vary-for-cache-rules/)).

**Pingora** (open source):
- Key = 128-bit primary hash, plus an optional variance hash built from a sorted map of
  header → value
  ([key.rs#L50-L72](https://github.com/cloudflare/pingora/blob/702f69015e53f7244d6ad2e743de571d859a70a4/pingora-cache/src/key.rs#L50-L72),
  [variance.rs#L1-L40](https://github.com/cloudflare/pingora/blob/702f69015e53f7244d6ad2e743de571d859a70a4/pingora-cache/src/variance.rs#L1-L40)).
- **Variant tombstone.** "When purging all the variance, only the primary slot is deleted; the
  provenance timestamp of the primary is the tombstone of all the variances". A variant created before
  `valid_after` is rejected at lookup
  ([lib.rs#L1564-L1576](https://github.com/cloudflare/pingora/blob/702f69015e53f7244d6ad2e743de571d859a70a4/pingora-cache/src/lib.rs#L1564-L1576),
  [#L1513-L1521](https://github.com/cloudflare/pingora/blob/702f69015e53f7244d6ad2e743de571d859a70a4/pingora-cache/src/lib.rs#L1513-L1521)).
- Purges distinguish `Delete` from `Expire` (mark stale, revalidate)
  ([storage.rs#L27-L64](https://github.com/cloudflare/pingora/blob/702f69015e53f7244d6ad2e743de571d859a70a4/pingora-cache/src/storage.rs#L27-L64)).

### 2.7 Akamai

**Invalidate vs Delete.** Invalidate marks content invalid, so the edge revalidates and may serve stale
when the origin is unreachable. Delete removes it
([purge methods](https://techdocs.akamai.com/purge-cache/docs/purge-methods)).

**Scopes.** Cache tags (at most 128 per object, 128 characters each)
([purge by cache tag](https://techdocs.akamai.com/purge-cache/docs/purge-content-cache-tag)).
CP code: all content of a content-provider code, the closest analogue of a HARP endpoint
([purge by CP code](https://techdocs.akamai.com/purge-cache/docs/purge-content-cp-code)).

**Internals.** The 2010 Akamai paper mentions configurable cache indexing and invalidation policies
but describes no purge data structure
([Nygren, Sitaraman, Sun 2010, §7.1](https://pdos.csail.mit.edu/6.824/papers/akamai.pdf)). No primary
source on Fast Purge internals was found.

### 2.8 Souin / Caddy cache-handler 1.7.9

**Key.** A flat string: `METHOD-scheme-host-path?query[-headers]`
([key.go#L92-L165](https://github.com/darkweak/souin/blob/v1.7.9/context/key.go#L92-L165)).

**Vary.** A mapping record `IDX_<base key>` holds a protobuf map from varied key to
`{stored_at, fresh_time, stale_time, varied_headers, etag}`
([storage.proto#L8-L22](https://github.com/darkweak/storages/blob/81250fe6fc63358ff9f12faa72b01f36e48ed60c/core/storage.proto#L8-L22)).
Writing it is a read-modify-write of the whole map
([core.go#L154-L195](https://github.com/darkweak/storages/blob/81250fe6fc63358ff9f12faa72b01f36e48ed60c/core/core.go#L154-L195)).
- The rueidis Redis backend does GET then SET with no transaction and no TTL, so concurrent variants
  can lose an entry
  ([redis.go#L178-L221](https://github.com/darkweak/storages/blob/81250fe6fc63358ff9f12faa72b01f36e48ed60c/redis/redis.go#L178-L221)).
- The go-redis backend stores one hash field per variant (`HSET`) instead
  ([go-redis.go#L357-L368](https://github.com/darkweak/storages/blob/81250fe6fc63358ff9f12faa72b01f36e48ed60c/go-redis/go-redis.go#L357-L368)).
- This is HARP's model and its weakness.

**Surrogate keys.** `SURROGATE_<tag>` holds a comma-joined key list, appended under an in-process
mutex. Each response is also tagged by its URI
([common.go#L192-L303](https://github.com/darkweak/souin/blob/v1.7.9/pkg/surrogate/providers/common.go#L192-L303)).
Lists are never pruned on expiry *(inference)*. Tags are written asynchronously after the body, so a
purge in between misses the entry
([middleware.go#L576-L586](https://github.com/darkweak/souin/blob/v1.7.9/pkg/middleware/middleware.go#L576-L586)).

**Purge API.** URI, prefix, origin and flush are all full scans (`GetAll`, `SCAN MATCH`, regex)
([souin.go#L246-L370](https://github.com/darkweak/souin/blob/v1.7.9/pkg/api/souin.go#L246-L370),
[redis.go#L255-L288](https://github.com/darkweak/storages/blob/81250fe6fc63358ff9f12faa72b01f36e48ed60c/redis/redis.go#L255-L288)).

**Link to a transaction.** `Cache-Status: Souin; …; key=<cache key>`
([middleware.go#L601](https://github.com/darkweak/souin/blob/v1.7.9/pkg/middleware/middleware.go#L601)).

### 2.9 Envoy cache filter 1.40 (work in progress)

**Status.** Both filters and both backends are `wip`
([extensions_metadata.yaml#L401-L412](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/extensions_metadata.yaml#L401-L412)).

**Key.** A proto of host, path, query and scheme, hashed to 64 bits. `cluster_name` is still a
placeholder
([key.proto#L6-L25](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/filters/http/cache/key.proto#L6-L25),
[http_cache.cc#L43-L60](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/filters/http/cache/http_cache.cc#L43-L60)).

**Vary.**
- `allowed_vary_headers` is an allowlist: a response varying on anything else is not cached
  ([cache.proto#L65-L77](https://github.com/envoyproxy/envoy/blob/v1.40.1/api/envoy/extensions/filters/http/cache/v3/cache.proto#L65-L77),
  [cache_headers_utils.cc#L374-L410](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/filters/http/cache/cache_headers_utils.cc#L374-L410)).
- A "vary marker" at the base key and the variant at key + vary-id, the Squid shape, with no list of
  the variants
  ([simple_http_cache.cc#L270-L310](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/http/cache/simple_http_cache/simple_http_cache.cc#L270-L310)).
- cache_v2 does not cache varied responses
  ([cache_sessions_impl.cc#L824-L826](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/filters/http/cache_v2/cache_sessions_impl.cc#L824-L826)).

**Invalidation.** There is no invalidation API
([http_cache.h#L271-L308](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/filters/http/cache/http_cache.h#L271-L308)).

**Eviction.** A full directory scan plus `stat`, then a sort
([cache_eviction_thread.cc#L91-L150](https://github.com/envoyproxy/envoy/blob/v1.40.1/source/extensions/http/cache/file_system_http_cache/cache_eviction_thread.cc#L91-L150)).

### 2.10 hishel 1.4.0 (HARP's RFC 9111 engine)

**Key.** `sha256(url)`, opaque
([_async_cache.py#L63-L70](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_async_cache.py#L63-L70)).

**Storage interface.** `create_entry`, `get_entries(key)` (all variants), `update_entry(id)` and
`remove_entry(id)`. There is no listing and no bulk operation
([_async_base.py#L11-L92](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_storages/_async_base.py#L11-L92)).
Variants are entries that share a key, and they are filtered at lookup
([_spec.py#L145-L247](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_spec.py#L145-L247)).

**SQLite.** One row per entry, `entries(id, cache_key, data, created_at, deleted_at)`, indexed on
`cache_key`, with metadata packed inside `data`. Cleanup scans the whole table every hour
([_async_sqlite.py#L149-L172](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_storages/_async_sqlite.py#L149-L172),
[#L401-L452](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_storages/_async_sqlite.py#L401-L452)).

**Redis.** `entry:{uuid}` with a TTL, plus a variant set `idx:{cache_key}` written in the same `MULTI`.
`get_entries` removes ids whose entry has expired, a lazy repair
([_async_redis.py#L53-L96](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_storages/_async_redis.py#L53-L96),
[#L169-L206](https://github.com/karpetrosyan/hishel/blob/e10e0230fc8fc161466c0588762a4706c83856db/src/hishel/_core/_storages/_async_redis.py#L169-L206)).
The interface is row-per-variant keyed by id, which a row-per-variant model fits better than HARP's
blob-per-key *(inference)*.

### 2.11 Redis patterns (redis.io)

- **SCAN** is "O(N) for a complete iteration", and "the MATCH filter is applied after elements are
  retrieved" ([SCAN](https://redis.io/docs/latest/commands/scan/)). KEYS: "consider using SCAN or
  sets" ([KEYS](https://redis.io/docs/latest/commands/keys/)).
- **Secondary indexes.** A sorted set with equal scores, read with `ZRANGE … BYLEX`, "is basically
  equivalent to a b-tree", and serves prefix queries as `"[p" "[p\xff"`. `ZCOUNT` is logarithmic.
  Index updates belong in `MULTI`/Lua, and drift is repaired by read repair or a `SCAN` rebuild
  ([indexes](https://redis.io/docs/latest/develop/clients/patterns/indexes/)).
- **Keyspace notifications** are fire-and-forget, and `expired` fires when the key is actually deleted.
  They cannot keep an index in sync
  ([keyspace notifications](https://redis.io/docs/latest/develop/pubsub/keyspace-notifications/)).
- **Client-side caching.** BCAST mode tracks prefixes rather than keys. A "caching-in-progress"
  placeholder deleted by the invalidation closes the fill race
  ([client-side caching](https://redis.io/docs/latest/develop/reference/client-side-caching/)).

### 2.12 Meta, CacheLib, Netflix, Rails

- **Leases (memcache, NSDI 2013, §3.2.1).** On a miss, the server hands out a "64-bit token bound to the
  specific key". A delete invalidates the token, so a stale set is refused, "similar to how
  load-link/store-conditional operates". Deletes are embedded in committed SQL and replayed by
  mcsqueal (§4.1)
  ([Nishtala et al.](https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf)).
- **CacheLib (OSDI 2020, §4).** A chained hash table at 31 B of DRAM per item, used for exact lookup
  only. Any grouping index has to live outside the engine *(inference)*
  ([Berg et al.](https://www.usenix.org/system/files/osdi20-berg.pdf)).
- **Facebook photos (SOSP 2013, §2.1).** Variants (dimensions) are encoded in the URL, so there is no
  Vary ([Huang et al.](https://www.cs.cornell.edu/~qhuang/papers/sosp_fbanalysis.pdf)).
- **Netflix Open Connect.** Proactive fill, with a central control plane that knows which file is on
  which appliance ([Open Connect Overview](https://openconnect.netflix.com/Open-Connect-Overview.pdf)).
  It describes no invalidation.
- **Namespace versioning.** memcached's "Deleting by namespace": a version key folded into every key
  ([ProgrammingTricks](https://github.com/memcached/memcached/wiki/ProgrammingTricks)).
- **Rails recyclable cache keys** moved the version out of the key because key-based expiry generates
  "lots of cache trash" ([rails#29092](https://github.com/rails/rails/pull/29092),
  [caching guide](https://guides.rubyonrails.org/caching_with_rails.html)).

### 2.13 Standards

- **RFC 9111.** The key is at minimum method + target URI (§2). An unsafe request invalidates the
  target URI, meaning "remove all stored responses whose target URI matches … or mark them as invalid",
  so all of its variants (§4.4) ([RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.4)).
- **RFC 9875 Cache Groups** (Oct 2025). `Cache-Groups` is a list of opaque strings scoped to the
  origin. `Cache-Group-Invalidation` on an unsafe response "MAY" invalidate a group
  ([RFC 9875](https://www.rfc-editor.org/rfc/rfc9875.html)). It is the standard form of surrogate keys.
- **RFC 9211 Cache-Status.** The `key` parameter is "a representation of the cache key", and `detail`
  is implementation-specific ([RFC 9211 §2.7-2.8](https://www.rfc-editor.org/rfc/rfc9211.html)). It is
  a standard carrier for "which entry served this".

---

## 3. Comparison

E = eager delete; L = lazy check at lookup; G = generation (versioning); S = full scan; — = not
supported. N = entries, V = variants of one URL, m = entries matched, R = active rules or bans.

| System | Key in index | Vary storage | List / stats | Exact | Prefix | Host / endpoint | All | Fill race | Multi-node |
|---|---|---|---|---|---|---|---|---|---|
| Varnish | SHA256, opaque | sibling objects under one objhead | — / per-object hits | E, O(V) | L ban, O(R) per hit + lurker | L ban, or xkey tag E O(m) | L ban | not closed: busy objects skipped | fan-out (Enterprise) |
| ATS | MD5, opaque, 10 B | vector in the first Doc (HARP's shape) | S with disk reads | E, O(1) dir | L regex rules | G per remap | G, or offline clear | closed (`dont_update_directory`) | none |
| nginx | MD5 in shm rbtree | variant at MD5(key+vary), unlinked | S / counters | E, O(log N) | L (Plus) or S | G (fork) | S or G | not closed | none |
| Squid | MD5 hash table | marker + variant at MD5(url+mark) | S / counters | E (one variant) | — | — | — | closed (private key) | HTCP CLR fan-out |
| Fastly | URL + secondary vary key | secondary key, ≤75 | n/p | E | via keys | key or purge-all | E | n/p | gossip broadcast |
| Cloudflare | URL (+ Vary headers) | variants under URL; Pingora tombstone | n/p | E | E via index (+ L queue) | E via index | E | L check vs pending queue | fan-out, per-machine index |
| Akamai | configurable | n/p | n/p | invalidate / delete | — | CP code | CP codes | n/p | "seconds" |
| Souin | flat string | mapping blob (HARP's shape) | S | E | S | S | S | not closed | shared store |
| Envoy | proto hash | marker + variant | — | — | — | — | — | — | none |
| hishel | sha256, opaque | rows sharing a key | — | E by id | — | — | — | — | — |
| **HARP today** | URL with endpoint as host | YAML blob of ≤8 | S decode | E, O(1) | S | S | S | closed in one process | not closed across instances |

n/p = not published.

---

## 4. Patterns that win, per operation

1. **List and browse per endpoint.** Every mature engine indexes by hash, and so none of them can list
   (Varnish, ATS, nginx, Squid, Envoy, hishel). Cloudflare had to add a separate per-machine index
   (CacheDB) to find entries by host or tag. **Winning pattern: keep the structured key
   `(endpoint, path, query)` in an ordered index**, a SQL B-tree or a Redis lex sorted set, next to
   the hash used for lookup.
2. **Show an entry with its variants.** ATS (first-Doc vector), Varnish (objhead → objcores), Pingora
   (primary + variance) and Souin (`IDX_`) all keep a primary record that leads to its variants.
   Markers without a back-link (nginx, Squid, Envoy) make an exact purge miss variants.
   **Winning pattern: a resource row and one row per variant**, not one blob rewritten per variant.
   That rewrite is the contention ATS names and the lost update Souin's Redis backend has.
3. **Link a transaction to its entry.** Varnish `X-Varnish` (object VXID), Souin `Cache-Status key=`,
   RFC 9211 `key`. **Winning pattern: a stable variant id** stamped on the served response and stored
   on the transaction.
4. **Statistics.** Engines keep counters: Varnish `oc->hits`, nginx `uses`, Squid and NGINX Plus
   rolling ratios. ykey computes per-key aggregates. **Winning pattern:** take the hit ratio from
   request outcomes (HARP's transactions already record `cached`), and keep size and hits per variant
   so that "volume per endpoint" and "biggest" are indexed aggregates. Batch the hit counter writes.
5. **Exact invalidation.** Universal: an eager O(1) delete of the resource, which takes all its
   variants (RFC 9111 §4.4, Fastly, Cloudflare). Pingora deletes only the primary and uses its
   timestamp as the tombstone for the variants.
6. **Prefix invalidation.** Three working designs:
   - a lazy rule checked at lookup (ATS regex_revalidate, NGINX Plus, Varnish bans);
   - an eager delete through an ordered index (Cloudflare CacheDB);
   - a tag per path segment (ykey `add_tree_keys`).
   The lazy rule alone accumulates (Varnish ban lists, `ban_cutoff`) and leaves dead bytes behind
   (Cloudflare's 10x). **Winning pattern: lazy at once, eager in the background** (Cloudflare 2024).
7. **Endpoint and everything.** Generations are O(1) and race-safe: ATS `cache.generation` per remap,
   the nginx fork, memcached namespaces. Their cost is garbage that must be collected (the Rails
   "cache trash").
8. **Fill vs invalidation.** Closed by ATS, Squid, memcache leases, Pingora `valid_after` and Redis
   placeholders. Left open by Varnish, nginx and Souin. **Winning pattern: record a monotonic stamp
   when the request sets out, and refuse at commit (and at lookup) any entry whose stamp predates a
   matching invalidation.** HARP already does this per process. To hold across instances, the stamp
   has to live in the shared store.
9. **Multi-node.** CDNs fan invalidations out because every node owns its storage. HARP's instances
   share one store (SQL or Redis), so an invalidation written to that store is seen by all of them, as
   with memcache's durable, replayable log. No fan-out is needed unless a node keeps a local L1
   *(inference)*.

---

## 5. Candidate models for HARP

Scale assumed: one to a few instances sharing one store, up to millions of variants. Bodies stay in
content-addressed blobs (deduplicated, already handled by the orphan sweep) in all three models.

Shared vocabulary:
- **resource**: method + endpoint + normalised URL. It is today's cache key.
- **variant**: one stored response under a resource, identified by its selecting headers.
- **seq**: a monotonic counter in the shared store: a SQL sequence or autoincrement, Redis `INCR`, a
  memory counter. It replaces wall-clock time for ordering, so clock skew between instances does not
  matter *(inference)*.

### Model A: indexed rows, eager delete (Cloudflare CacheDB, without the queue)

**Layout.**
- SQL:
  - `cache_resources(key PK, endpoint, path, query, method)`, indexed on `(endpoint, path)`;
  - `cache_variants(id PK, resource_key FK ON DELETE CASCADE, selecting_hash, status, size,
    stored_at, expires_at, hits, last_hit_at, headers_blob, body_blob)`, indexed on `expires_at` and
    `(resource_key)`.
- Redis:
  - a hash per resource and a hash per variant;
  - a set `variants:{resource}`;
  - per-endpoint lex sorted sets `paths:{endpoint}`;
  - sorted sets `by_expiry` and `by_size:{endpoint}`;
  - per-endpoint counters (`HINCRBY` count and bytes);
  - all written in one `MULTI` or Lua script.
- Memory: dicts plus a sorted list per endpoint (`bisect`) and a heap for expiry.

**Operations.**
- Lookup: one point read per resource, plus its variants.
- List: an index range.
- Stats: `GROUP BY endpoint` (SQL) or counters (Redis).
- Exact invalidation: delete the resource, cascading to its variants.
- Prefix: `DELETE … WHERE endpoint=? AND path >= p AND path < p||'￿'` in batches, or a `BYLEX`
  range on Redis.
- Endpoint and all: batched deletes of O(m) rows.
- Expiry: a range on `expires_at`, so no decoding sweep.

**Fill race.** Today's stamp log moves into the store, as a seq per invalidated scope.

**Trade-offs.**
- (+) Simplest mental model; the index is the truth; nothing lingers.
- (−) Invalidating a big endpoint or everything is O(m) work before it takes effect. A request racing
  that delete can still be served from a row not yet deleted, unless a generation check is added,
  which leads to Model C.
- (−) On Redis, every write maintains five structures.

### Model B: generations and rules, lazy only (ATS generation + regex_revalidate + Varnish bans)

**Layout.**
- Variants store `fill_seq`: the seq read when their request set out.
- A small table or hash `cache_invalidations(scope, value, seq)`, where scope is `all`, `endpoint`,
  `prefix` (endpoint + path prefix) or `resource`.

**Lookup.** A variant is valid only if `fill_seq` is greater than the newest seq among:
- `all`;
- its endpoint;
- each prefix of its path, at most one per path segment (Cloudflare caps prefixes at 31 separators);
- its resource.

That is O(path segments) point reads, or one cached read of the whole rules set, which stays small.

**Operations.** Every invalidation is O(1) to issue. Expiry is still needed to reclaim space, and
listing has to apply the same rules to hide dead rows.

**Trade-offs.**
- (+) Instant invalidation of any scope.
- (+) Race-safe by construction: the check at commit and at lookup is the same comparison.
- (+) Works the same on all backends.
- (−) Purged bytes stay until TTL expiry (the Cloudflare and Rails lesson).
- (−) Rules accumulate unless something retires them (Varnish bans, `ban_cutoff`).
- (−) Every lookup pays the rule check.
- (−) Without an index, listing still scans. B alone does not meet the browsing requirement.

### Model C: indexed rows + invalidation log, lazy then eager (Cloudflare 2024 hybrid)

Model A's layout plus Model B's `cache_invalidations` log and `fill_seq` on each variant.

**Invalidation.** Write the rule (O(1)), and it takes effect at once for lookups, commits and listings.
A background worker deletes what it covers through the index, in batches (Varnish's lurker, done with
ranges instead of predicates). Once nothing older than its seq can match, it retires the rule:
- a `resource` rule right away;
- a `prefix` or `endpoint` rule after the range delete;
- `all` after a full pass, which can also be a table truncate.

**Commit.** A fill whose `fill_seq` predates a matching rule is refused. This replaces the
per-process stamp log with the same comparison against the shared log, closing the race across
instances.

**Lookup.**
- Resource row and variants: one indexed read.
- Rule check: the newest seq for `all`, the endpoint and the path's prefixes. With rules retired
  quickly, the live set stays tiny, so each instance can hold it in memory, refreshed when its maximum
  seq changes (one cheap read).

**Statistics** and **expiry** work as in Model A. The rule check is applied to listings too, so the
explorer never shows a dead entry.

**Trade-offs.**
- (+) Every operation in the brief is either indexed or O(1).
- (+) Invalidation of any scope is instant and race-safe, and purged bytes are reclaimed within one
  worker pass.
- (−) The most moving parts.
- (−) The worker and rule retirement need tests for the corner cases (a rule retired while a fill
  with an old seq is still in flight: keep a retired rule until no in-flight request is older than
  it; Varnish solves the same problem with ban refcounts).

### Fit per backend

| | SQL | Redis | Memory |
|---|---|---|---|
| A | native: B-tree ranges, cascade, `GROUP BY` | five structures per write, Lua for atomicity; drift possible, needs repair ([indexes](https://redis.io/docs/latest/develop/clients/patterns/indexes/)) | dicts + sorted lists; trivial |
| B | rule table tiny; rows need no index beyond the key | rule hash tiny; TTL on keys reclaims space natively | trivial |
| C | A + B; the worker is a batched `DELETE` by range | A + B; Redis key TTL can stand in for the expiry sweep, with lazy removal of dangling index members, as hishel does | trivial |

The decisions doc says "the cache never depends on SQL, even on Redis" (decision 2). All three models
keep that: each backend implements the same logical layout with its own structures. Model A or C would
**replace** decision 2's derived `http_cache_entries` index: the store becomes indexed itself, so there
is nothing to keep in sync. That needs a call from the team.

---

## 6. Recommendation

**Model C.** It is the shape Cloudflare converged on after running the lazy-only model at scale and
paying for it in storage. Its parts are each proven:
- the resource → variants layout of ATS, Varnish and Pingora;
- scoped generations, as in ATS per remap;
- a predicate log retired by a background worker, as Varnish does;
- the fill-race guard of memcache leases.

HARP's current code already holds the seeds: `invalidate()`, the stamp, and the per-key lock. Model C
moves them into the shared store and puts each variant on its own row.

To de-risk, Model C can ship in two steps:
1. **Model A layout + `all` and `endpoint` rules.** These rules are the cheap ones: one point read
   each, and they cover the large invalidations that eager deletion makes slow.
2. **Prefix rules and the worker.**

**Expected costs at a few million variants** *(inference)*:
- lookup: one indexed read, plus one in-memory rule check;
- listing: an index range;
- invalidation of any scope: one row written;
- reclaiming space: one batched range delete per rule.

---

## 7. Gaps and unverified points

- Fastly's purge-all implementation and its fill-vs-purge behaviour are not published.
- Akamai Fast Purge internals are not published. The Akamai API summary page was seen only as a search
  snippet.
- Cloudflare's behaviour for fills that race a purge is not stated. The insert-timestamp comparison
  implies they are rejected *(inference)*.
- hishel 1.4.0: no RFC 9111 §4.4 invalidation was found in `_spec.py`. The absence was checked only by
  grep, and HARP implements §4.4 itself (`invalidate`).
- ATS per-remap generation relies on `conf_remap` overridability. The conf_remap page itself was not
  fetched.
- The Varnish in-flight fetch vs ban behaviour is inferred from the code (checkpoint taken at unbusy),
  not quoted from the docs.
