# mcp: search and read transactions

**Problem**

The first thing an agent debugging an integration needs is to find the failing exchanges and read them.

**Acceptance criteria**

- `search_transactions` (Viewer): `from` and `to` required, at most `mcp.max_window` apart; optional `endpoint`, `method`, `status` (a code or a class such as `5xx`), `text` (message summaries), `cursor`. Returns at most `mcp.max_page` summaries newest first (`id`, `started_at`, `endpoint`, method and path, status, duration, `cached`, `error`), `next_cursor`, and the total when it is known within the time limit. A window too wide or a query over the time limit returns a readable tool error telling the agent to narrow its window (tests). Built on child 2.
- `get_transaction` (Viewer): `id`; metadata, request and response with headers as stored (credentials redacted by #1140) and sizes, tags, markers, error. Bodies only when `mcp.bodies` is on: text bodies truncated to `mcp.max_body_size`, binary bodies never (tests for each case).
- Tool descriptions tell the agent to search a narrow window first, then open details.

**Out of scope**

Searching inside bodies.
