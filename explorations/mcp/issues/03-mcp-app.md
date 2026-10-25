# mcp: the application, its tokens and its quotas

**Problem**

Agents need a protocol endpoint, and the Operator needs to decide whether its transactions are exposed to them at all.

**Acceptance criteria**

- `harp_apps/mcp`, not in the default applications, enabled by adding it to `applications`; the `mcp` SDK comes with the extra `harp-proxy[mcp]`. Enabled without the extra, startup fails with a message naming the extra.
- Declares `dashboard`, `storage` and `proxy` in its dependencies; serves Streamable HTTP under `/mcp` on the dashboard port (child 1).
- Accepts `Authorization: Bearer harp_…` only (explore/auth #1522); a browser session or Basic is refused. The actor context (account, role, token) is available to tools.
- `tools/list` holds only the tools the actor's role allows (Viewer: transactions; Editor: also endpoints).
- Quota: 60 calls per minute per token (setting), in memory per instance; above it, a tool error with a retry delay (test).
- Settings: `mcp.bodies` (off), `mcp.max_body_size`, `mcp.max_window` (7 days), `mcp.max_page` (200), `mcp.query_timeout` (2 s), `mcp.calls_per_minute` (60).

**Out of scope**

The tools themselves (children 4, 5); OAuth (child 7).
