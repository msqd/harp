# mcp: endpoints and their remotes

**Problem**

When calls fail, an agent needs to know whether a remote is down before reading transactions.

**Acceptance criteria**

- `get_endpoints` (Editor only; absent from `tools/list` for a Viewer): per endpoint, its name and each remote's url, state (up, down, checking), error rate and median latency over the last hour.
- When storage shed transactions in that hour, the figures are flagged incomplete (as #1141 does for the overview).

**Out of scope**

Acting on remotes.
