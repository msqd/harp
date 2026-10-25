# docs: operating the cache store

**Problem**

The store's requirements and behaviour change for operators.

**Acceptance criteria**

- The http_cache docs describe the store per backend, invalidation (scopes, soft and hard), the background reclamation, and statistics.
- Upgrading: the cache is dropped once.
- Redis: the required `maxmemory-policy` and why.
- Memory backend: invalidation is per instance.

**Out of scope**

Tuning guides.
