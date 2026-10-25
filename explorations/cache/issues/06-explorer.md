# dashboard: the cache explorer

**Problem**

Nobody can see what the cache holds or how well it works.

**Acceptance criteria**

- A Cache page (Viewer and above) in today's dashboard: entries per endpoint with URL, status, size, age, remaining freshness and uses, sorted and filtered, paginated from the store's index.
- An entry's detail: its variants with the `Vary` headers that select them, stored headers, `Cache-Control` directives and why it is still fresh, a body preview under the transaction body rules.
- Statistics: hit ratio per endpoint (from transactions' cache outcome, child 5), volume per endpoint, largest entries.
- From a transaction served by the cache, a link to its entry and variant; from an entry, the transactions it served.

**Out of scope**

Invalidation (child 7); the `/next` dashboard.
