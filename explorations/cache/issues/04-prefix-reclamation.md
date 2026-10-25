# http_cache: prefix invalidation and background reclamation

**Problem**

Invalidating a URL prefix is the common case after an upstream change, and bans must not pile up.

**Acceptance criteria**

- Prefix bans, cut at path-segment boundaries (`/api/users` covers `/api/users/42`, not `/api/usersx`); the lookup check costs a bounded number of reads for a key of depth d, whatever the number of entries or bans.
- A background worker (janitor) deletes by range the entries each ban covers, then retires the ban; batched, bounded per run, resumable. Test that a retired ban never lets a covered entry come back.
- Retired bans and orphaned bodies are reclaimed; counters stay exact.

**Out of scope**

Tag-based invalidation.
