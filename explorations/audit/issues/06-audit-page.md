# dashboard: the Audit page and "My activity"

**Problem**

The audit is useless if nobody can read it.

**Acceptance criteria**

- Admins: an Audit page listing events newest first, paginated, filtered by period, actor, action and target; the API behind it requires the Admin role.
- Every account: "My account" shows its own sign-ins, sessions, tokens and identities events; the API returns only events whose actor or target is the current account.
- Viewers and Editors never see another account's events (test per role).
- No MCP tool exposes the audit.

**Out of scope**

Export (the SIEM is fed by the log stream).
