# http_cache: invalidation log for keys, endpoints and everything, race-safe

**Problem**

Removing entries must not cost a scan, and a fetch that started before an invalidation must never store its now-stale response after it, on any number of instances.

**Acceptance criteria**

- An invalidation appends a ban `(seq, kind, key or prefix, mode)`, `seq` allocated by a counter record in the shared store (`UPDATE … RETURNING` on PostgreSQL, not a sequence). Kinds in this child: exact key, endpoint, everything. Modes: soft (entries stale, revalidated with their validators, RFC 9111 §4.4) and hard (unusable).
- Lookup checks bans in the same round trip (PostgreSQL `NOT EXISTS`, a Redis Lua script, a dictionary in memory); a banned entry is never served as fresh.
- Each entry is stamped with the counter read before its origin fetch; storing an entry whose stamp is below a matching ban is refused. Test the race with two concurrent tasks on PostgreSQL and Redis.
- Unsafe-method invalidation (RFC 9111 §4.4, today's behaviour from #909) becomes an exact-key ban with no actor.

**Out of scope**

Prefix bans and reclamation (child 4).
