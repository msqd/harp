# dashboard: invalidation by editors, audited

**Problem**

An operator who sees a bad entry must be able to remove it, and the audit must say who did.

**Acceptance criteria**

- Editors invalidate an entry, a URL prefix on an endpoint, an endpoint, or everything, soft by default with a "hard" choice; everything asks to type `invalidate`. A preview shows an approximate count before confirming.
- Each invalidation runs in a unit of work and records the auditable event `http_cache.invalidated` (scope, key or prefix, mode, count) with the Editor as actor; a Viewer's attempt records `denied` (explore/audit).
- With the memory backend, the page states that only the instance answering is invalidated.

**Out of scope**

Invalidation from MCP.
