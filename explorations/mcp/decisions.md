# explore/mcp: decisions from the grill

Decisions taken while grilling explore/mcp (2026-10-25). Built on explore/auth (tokens, actor
context, roles) and the brainstorm (`explorations/brainstorm.md`, section MCP).

Facts from the code: transaction search filters on endpoint, method, status, flag, tpdex, and a
`LIKE %…%` text search over endpoint and message summaries (`harp_apps/storage/services/sql.py:111-124`,
an unbounded scan); no period filter yet (#1037, 0.14); indexes on `started_at`, `endpoint`,
`x_method`, `x_status_class`; no MCP SDK in the dependencies.

1. Bodies: not exposed by default. A transaction's detail gives metadata and headers (credentials
   already redacted by #1140). `mcp.bodies`, enabled explicitly by the Operator, exposes text
   bodies truncated to a maximum size per message; binary bodies are never exposed. Reason: what
   an agent reads leaves the Operator's infrastructure for the LLM provider.
2. Tools follow the dashboard's role tiers (explore/auth decision 20), with no MCP exception: a Viewer
   token gets `search_transactions` and `get_transaction`; an Editor token also gets `get_endpoints`
   (remotes, state, recent error rate). A tool outside the actor's role is absent from `tools/list`.
3. Guards, all settings: `from` and `to` required, window up to 7 days, reaching back to the
   retention limit (index on `started_at`); text search over message summaries only, inside the
   window, never bodies; at most 200 transaction summaries per page, with a cursor (detail through
   `get_transaction`); SQL timeout 2 s per query (PostgreSQL `statement_timeout`, MySQL
   `MAX_EXECUTION_TIME`, asyncio timeout on SQLite), answered as a readable tool error telling the
   agent to narrow the window; 60 calls per minute per token, in-memory per instance, answered
   with a retry delay. Shares its period query with the dashboard's #1037.
4. Protocol: the official `mcp` SDK, as the optional extra `harp-proxy[mcp]`, mounted as an ASGI
   sub-application. The kernel gains a real controller that delegates to an ASGI app (the
   `AlreadyHandledHttpResponse` hand-off at `harp/asgi/kernel.py:66`, used today by a workaround in
   `harp_apps/dashboard/controllers/__init__.py:127-142`), which the dashboard's static assets can
   then use too. The SDK follows the fast-moving spec (2025-03-26, 2025-06-18, 2025-11-25).
5. App: `harp_apps/mcp`, not in the default applications, added explicitly to `applications` and
   usable only with the `[mcp]` extra installed (without it, startup fails saying what to install).
   Declares `dashboard`, `storage` and `proxy` in its dependencies; served under `/mcp` on the
   dashboard port. Accepts `Bearer harp_…` tokens only, never browser sessions, so every MCP call
   hangs on a revocable token. Calls are reads: not audited (explore/audit decision 14), counted
   by the quotas.
6. Tools, first iteration (tools only, no MCP resources nor prompts; descriptions teach the agent
   to search a narrow window first, then open the detail):
   - `search_transactions` (Viewer): `from`, `to` (required, 7 days at most), `endpoint`,
     `method`, `status` (code or class such as `5xx`), `text` (summaries), `cursor`; returns up to
     200 summaries newest first (`id`, `started_at`, `endpoint`, method and path, status,
     duration, `cached`, `error`), `next_cursor`, and the total when known within the timeout.
   - `get_transaction` (Viewer): `id`; returns metadata, request and response with redacted
     headers and sizes, bodies only under `mcp.bodies` (text, truncated, never binary), tags,
     markers, error.
   - `get_endpoints` (Editor): no input; per endpoint, its remotes with url, state, error rate and
     median latency over the last hour, flagged incomplete when storage shed data (as #1141 does
     for the overview).
7. OAuth for MCP clients goes first through an external IdP as authorization server (explore/auth
   decision 27): RFC 9728 protected resource metadata, access tokens for HARP's audience resolved
   to an identity by (issuer, sub), scopes capping the role. Kept as the last child of this
   exploration, after Bearer tokens work end to end.
