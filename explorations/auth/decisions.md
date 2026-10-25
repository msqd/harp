# explore/auth: decisions from the grill

Decisions taken while grilling explore/auth (2026-10-24). Vocabulary lives in `CONTEXT.md`; this file
holds the design choices.

1. Roles are Viewer, Editor, Admin, ordered. Admin is a role, not the Operator.
2. What signs in is an Account (person or machine). Tables: `auth_accounts`, `auth_identities`,
   `auth_tokens`, `auth_sessions`.
3. Sign-in method (enabled by the Operator) vs Identity (account ↔ method). Disabling a method
   suspends its identities without deleting them.
4. Sessions are server-side rows in `auth_sessions`; the signed cookie carries only the session id.
   `session_epoch` is dropped. Gives per-device sign-out, a sessions list, server-enforced idle
   timeout, and a session the audit can point to.
5. Session lifetime defaults: ends after 12 h idle, and after 7 days whatever the activity. Both
   are settings.
6. Accounts declared in configuration are deprecated. The first Admin comes from the CLI
   (`harp auth:create-account`, also the access-recovery path) or from a one-time setup link HARP
   logs at startup while no Admin exists. Existing Basic users are imported once by the migration.
7. Nobody enters without an invitation from an Admin, whatever the sign-in method: no account is
   created on the fly at first OIDC sign-in, and there is no claim-to-role mapping. The setup link
   is an invitation to the Admin role.
8. An invitation is single-use, expires after 72 h (setting), lets the invitee pick any enabled
   method, may name an expected email that an OIDC acceptance must match with `email_verified`,
   and can be listed and revoked by an Admin.
9. An account links another identity from its own session, after re-authenticating when the
   session is older than 15 minutes; never by matching emails. It may remove any identity but its
   last; an Admin may remove any. Removing an identity revokes the sessions it opened.
10. No open mode. The dashboard declares `auth` in its `dependencies`, so auth is loaded whenever a
    dashboard is; a HARP without dashboard loads no auth (no app is mandatory, see explore/audit
    decision 6). The system account `anonymous` stays only as the author of existing flags and is
    never resolved for a request again.
11. With no sign-in method configured, the password method is enabled, with no account and no
    default credentials. Nobody signs in before accepting the setup link (an invitation to the
    Admin role) that HARP logs while no Admin exists. Proxied traffic is never blocked.
12. New passwords are hashed with Argon2id (argon2-cffi, OWASP parameters 19 MiB / t=2), with a cap
    on concurrent verifications. Basic hashes are taken over by type: pbkdf2_sha256 and argon2
    imported then re-hashed at next sign-in; plaintext hashed at import; any other algorithm
    imported without a password, with a warning to re-invite. passlib stays out of the auth app.
13. Password policy per NIST 800-63B-4: 15 to 256 characters, a bundled list of the 10 000 most
    common passwords refused, no composition rules, no forced expiry. Failed sign-ins slow down
    per account and per IP with a growing delay, never a permanent lockout. No external breach
    lookup by default.
14. Token format `harp_<prefix 8><secret 43><crc32 6>`, base62, no `_` after `harp_`. Secret stored
    as SHA-256; prefix unique and indexed; checksum rejects typos before any lookup. Expiry is
    mandatory: 90 days by default, 365 at most (settings), warned 7 days ahead.
15. Every account creates its own tokens, with at most its own role (Viewer included). Machine
    accounts and their tokens are created by an Admin. An Admin lists and revokes every token; a
    secret is shown once, at creation. Effective role is min(token role, owner role), computed per
    request, so demoting or disabling an owner caps its tokens at once.
16. The proxy always strips HARP's own credentials before forwarding to an origin: its session
    cookie and any `Bearer harp_…`. No setting disables it; the strip is recorded on the
    transaction. Cookie is `__Host-` prefixed over HTTPS, HttpOnly, SameSite=Lax. Deliberate
    exception to ADR-0001: ADR candidate.
17. Migrations: one alembic environment, one branch per app (`branch_label`, the app's own
    `migrations/versions`). `version_locations` is a static list of every `harp_apps` app that has
    migrations, whether enabled or not, so a disabled app never leaves an unknown revision in
    `alembic_version`; a disabled app's tables exist, empty. `alembic_version` holds one row per
    app head. Boot, test fixtures and CLI move from `head` to `heads`; `ensure_schema_is_current`
    checks every head. All models share storage's `Base` (in-memory SQLite uses `create_all`);
    autogenerate filters per app with `include_object` on the table prefix. Cross-app order uses
    `depends_on`. The storage branch first gets a `naming_convention` migration (shippable on
    main); auth's first revision depends on it and renames `users` to `auth_accounts`. External
    plugin migrations are out of scope. ADR to write.
18. Account email is optional, unique, case-insensitive (stored lower-cased), never a way in.
19. OIDC: authorization code + PKCE S256, single-use nonce and state, one callback URL per provider
    and `iss` checked (RFC 9207) against mix-up, issuer discovery, `Referrer-Policy: no-referrer`
    on the callback. An OIDC identity is keyed on (issuer, sub), never on email nor on the
    provider's configured name, so renaming a provider in settings orphans nothing.
20. Visibility by role. Viewer: overview, transactions with bodies, metrics. Editor: also topology
    and storage state. Admin: also settings, dependencies, accounts, tokens, invitations.
21. An existing `dashboard.auth.type: basic` config keeps working: it enables the password and Basic
    methods, its accounts are imported once (decision 12), then its `users` list is ignored with a
    warning if it changes. Startup warns that Basic is deprecated. Basic is removed one minor
    version after the auth app ships.
22. explore/auth delivers Bearer tokens only. OAuth for MCP (RFC 9728 metadata, delegation to the
    IdP, dynamic client registration) moves to explore/mcp as an open question.
23. CSRF on cookie sessions relies on #1324 (0.13): Origin / Sec-Fetch-Site check and JSON content
    type on state-changing routes. The existing `PUT /api/system/proxy` (endpoint up/down) is an
    Editor action and an audit event.
24. explore/auth runs as a parallel sprint: an epic (outside the milestone) and its children in
    the `explore/auth` milestone, each child a test-first PR into the long-running `explore/auth`
    branch, coded by engineers under /lead-the-team. Order: storage naming_convention, alembic
    branch per app, auth app taking over `users` with roles, password and sessions with setup
    link, credential strip, tokens, invitations, identity linking and OIDC, Basic compatibility.
    The topic returns to main in one PR once the user accepts it, through a regular sprint's
    gates. Nothing reaches GitHub without the user's OK.
25. Resolving a request yields one actor context: account, effective role, `via` (session, token,
    later access token), `via_id`, and an optional client. Controllers, role checks and the audit
    depend only on it, never on `request.extensions["user"]`. So "Alice through an agent" stays
    distinguishable from "Alice" when MCP OAuth arrives, without touching controllers or audit rows.
26. One capping rule, written once in the resolver: effective role = min(account role, cap of the
    credential). A token's cap is its role; an IdP access token's cap will be its scopes.
27. No `agent` account kind: an agent acting for a person is that person's account with a client;
    an autonomous agent is a machine account. MCP OAuth (explore/mcp) goes first through an
    external IdP as authorization server: an access token for HARP's audience resolves to an
    existing identity by (issuer, sub), with no new table. HARP as its own authorization server
    stays additive (client id, kind and parent on tokens, a one-time codes table) if ever needed.
28. SQLite is never migrated by alembic: `_do_migrate` runs `create_all` on SQLite
    (`harp_apps/storage/utils/migrations.py:141-148`, "drop/recreate is fine when harp is
    upgraded"). Taking over `users` therefore happens on PostgreSQL and MySQL only; an existing
    SQLite database is recreated on upgrade, as today. ADR-0011's SQLite batch argument for the
    naming convention is moot; the convention still serves PostgreSQL and MySQL.
29. Token checksum (clarifies 14): CRC32 over every character before the last six, `harp_`
    included, written as six zero-padded base62 characters. Format, cookie names
    (`__Host-harp_session` over HTTPS, `harp_session` otherwise) and the strip live in the core
    contract `harp/security/credentials.py` (#1521); the auth app generates tokens with it (#1522).
30. The strip runs right after the request filters, before the transaction is recorded, so HARP's
    session cookie and HARP bearer tokens reach neither the origin nor the transaction record,
    whatever ADR-0009 redaction settings say (found by the adversarial review of #1575). It covers
    `Authorization: Bearer harp_…` and the two session cookies only: a HARP token placed elsewhere
    (query, other scheme, custom header) is the caller's mistake (user's decision, 2026-10-25).
31. One parser for HARP tokens in `Authorization`: the auth app reuses `harp/security/credentials.py`
    and accepts nothing more lenient, so no form accepted by auth escapes the proxy's strip.
32. Responses too: the proxy strips from origin responses every `Set-Cookie` named `harp_session` or
    `__Host-harp_session`, so an origin cannot plant or overwrite a dashboard session (`__Host-` does
    not pin a port). In #1521; ADR-0010 covers both directions.
33. Same-site CSRF across ports (SameSite ignores ports): state-changing dashboard routes require a
    same-origin request (#1586), on top of #1324 left unchanged in 0.13; the docs recommend a
    hostname of its own for the dashboard.
34. MySQL and MariaDB are treated as unsupported in these explorations (deprecated by ADR-0005,
    support being removed; user, 2026-10-25): design, code and tests target PostgreSQL (production)
    and SQLite (dev, `create_all`). New revisions may be no-ops on MySQL with a warning.
