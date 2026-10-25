# Epic: a cache explorer, with invalidation for editors

**Problem**

An operator cannot see what the cache holds, why a response is still served, or how effective the cache is, and cannot remove a bad entry short of waiting for its lifetime or wiping the storage. The store cannot answer these questions cheaply: one blob per cache key, found by id or by scanning everything.

**Outcome**

The cache store is indexed on every backend and invalidation is a numbered log checked at lookup, reclaimed in the background (ADR-0014). The dashboard lists entries per endpoint, shows an entry with its variants and freshness, links a transaction to the entry that served it, and shows cache statistics. An Editor invalidates an entry, a URL prefix, an endpoint or everything, softly (revalidate) by default or hard, each invalidation an audit event.

Design and decisions, on branch `explore/cache` (branched from `explore/audit`): `CONTEXT.md` (Cache Entry, Variant, Invalidation, Expiry), `explorations/cache/decisions.md`, ADR-0014, research in `explorations/cache/research/`.

**Children** (milestone explore/cache, PRs into branch `explore/cache`)

1. http_cache: an indexed store on PostgreSQL, SQLite and memory
2. http_cache: the indexed store on Redis
3. http_cache: invalidation log for keys, endpoints and everything, race-safe
4. http_cache: prefix invalidation and background reclamation
5. #404 transactions: detailed cache outcome per transaction
6. dashboard: the cache explorer
7. dashboard: invalidation by editors, audited
8. http_cache: PURGE as an invalidation
9. docs: operating the cache store

**Out of scope**

Purge across HARP instances without a shared store (memory backend); tag or surrogate-key invalidation.
