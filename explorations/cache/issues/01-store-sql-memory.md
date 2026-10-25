# http_cache: an indexed store on PostgreSQL, SQLite and memory

**Problem**

The cache keeps one `cache/meta` blob per key with its variants (`harp_apps/http_cache/adapters.py:55-60, 155`): listing, counting or invalidating by endpoint means scanning every blob. ADR-0014 (branch `explore/cache`) replaces it.

**Acceptance criteria**

- A store for hishel, replacing today's adapter, with one resource record per cache key and one variant record per `Vary` combination, ordered by endpoint then path. PostgreSQL and SQLite: tables in the http_cache alembic branch (`http_cache_` prefix), key column `COLLATE "C"` on PostgreSQL. Memory: equivalent in-process structures.
- Bodies stored by content digest, shared by records carrying the same body, removed when no record references them.
- RFC 9111 compliance is unchanged: the cache-tests baseline (`make test-e2e-cache`, ADR-0003) does not regress on any backend.
- Counters kept on write per endpoint (entries, bytes); the largest entries readable from an index on size.
- The existing cache is dropped at upgrade, said in the changelog.

**Out of scope**

Redis (child 2); invalidation (children 3, 4).
