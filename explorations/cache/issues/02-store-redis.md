# http_cache: the indexed store on Redis

**Problem**

The Redis blob storage is a supported cache backend; the indexed model of child 1 needs its Redis layout.

**Acceptance criteria**

- Resource and variant records as Redis hashes, an ordered index per endpoint as a lex sorted set, bodies by content digest kept alive as long as a record references them (expiry extended with `PEXPIREAT GT`, no reference count).
- Same behaviour and the same cache-tests baseline as child 1.
- Startup refuses, with a message, a Redis whose `maxmemory-policy` is not `volatile-*` or `noeviction` (eviction would drop bans; see child 3).

**Out of scope**

Redis Cluster.
