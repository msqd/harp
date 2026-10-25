# Epic: a read-only MCP server for debugging with agents

**Problem**

Debugging an integration through HARP means reading transactions by hand in the dashboard. An agent could search and read them, but HARP speaks no protocol an agent understands, and an unbounded search over the transaction record would stall the database.

**Outcome**

An optional application `harp_apps/mcp`, installed with the `[mcp]` extra and enabled explicitly, serves the Model Context Protocol under `/mcp` on the dashboard port, through the official SDK. It accepts HARP tokens only and offers three read-only tools that follow the dashboard's role tiers: `search_transactions` and `get_transaction` for Viewers, `get_endpoints` for Editors. Every search is bounded (time window, page size, SQL timeout, quota per token); bodies stay out unless the Operator turns them on. OAuth for MCP clients comes last, through an external identity provider.

Design and decisions, on branch `explore/mcp` (branched from `explore/auth`): `explorations/mcp/decisions.md`.

**Children** (milestone explore/mcp, PRs into branch `explore/mcp`)

1. kernel: a controller that delegates to an ASGI application
2. storage: a period-bounded transaction query with a time limit
3. mcp: the application, its tokens and its quotas
4. mcp: search and read transactions
5. mcp: endpoints and their remotes
6. docs: connecting an MCP client to HARP
7. mcp: OAuth through an external identity provider

**Out of scope**

Write tools; full-text search over bodies; MCP resources and prompts; HARP as an authorization server.
