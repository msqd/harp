# Epic: accounts, sign-in methods and tokens in an auth app

**Problem**

The dashboard knows one way in, HTTP Basic against users declared in the configuration, and one level of access: whoever passes Basic can do everything. There is no sign-out, no single sign-on, no credential for a machine, and no way to tell who did what. The coming cache invalidation, audit trail and MCP server all need an account with a role behind each request.

**Outcome**

A new `auth` application, always loaded, owns accounts, identities, sessions, tokens and invitations (`auth_*` tables, taking over `users`). Roles are Viewer, Editor, Admin. Sign-in methods are password (web form and server-side sessions), OpenID Connect providers, tokens, and HTTP Basic (deprecated). Nobody enters without an invitation; the first Admin accepts a setup link HARP logs. The proxy never forwards HARP's own credentials to an origin.

Design, vocabulary and decisions: `CONTEXT.md` (Access), `explorations/auth/decisions.md`, ADR-0010 and ADR-0011 on branch `explore/auth`.

**Children** (milestone [explore/auth](https://github.com/msqd/harp/milestone/24), PRs into branch `explore/auth`)

1. storage: name every constraint (naming_convention)
2. migrations: one alembic branch per application
3. auth: take over `users` as `auth_accounts`, with roles enforced per route
4. auth: password sign-in, server-side sessions, setup link
5. proxy: strip HARP's own credentials before the origin
6. auth: tokens
7. auth: invitations and account administration
8. auth: OpenID Connect providers and identity linking
9. auth: Basic configurations keep working, deprecated

**Out of scope**

OAuth for MCP clients (explore/mcp); the audit trail (explore/audit); multi-factor authentication; external plugins bringing tables.
