# auth: tokens

**Problem**

Scripts, CI jobs and MCP clients can only use Basic, with a person's password. There is no credential for a machine, nothing that expires, and nothing an Admin can revoke without changing a password.

**Acceptance criteria**

- `auth_tokens` (`account_id`, `name`, `prefix` unique, `secret_hash` SHA-256, `role` nullable, `created_at`, `expires_at` required, `last_used_at` at most once a minute, `revoked_at`).
- Format `harp_<prefix 8><secret 43><crc32 6>`, base62, no `_` after `harp_`; the secret is shown once at creation. A malformed or bad-checksum token is rejected before any database lookup.
- `Authorization: Bearer harp_…` authenticates as the token's account. Effective role is `min(token role, account role)`, computed per request: demoting or disabling the account caps its tokens at once (test).
- Expiry is mandatory: 90 days by default, 365 at most (settings); the UI warns 7 days ahead.
- Every account creates and revokes its own tokens, with at most its own role. An Admin creates machine accounts and their tokens, and lists and revokes every token.
- The token sign-in method is enabled explicitly in the settings.

**Out of scope**

OAuth access tokens issued by an identity provider (explore/mcp).
