# auth: password sign-in, server-side sessions, setup link

**Problem**

Basic makes the browser prompt on every visit, cannot sign out, and checks a hash on every request. There is no first-run path that does not ship credentials in the configuration.

**Acceptance criteria**

- `auth_identities` (`account_id`, `method`, `issuer`, `subject`, `password_hash`, `created_at`, `last_sign_in_at`, unique `(method, issuer, subject)`) and `auth_sessions` (`account_id`, `identity_id`, `created_at`, `last_seen_at` at most once a minute, `expires_at`, `revoked_at`, `user_agent`, `ip`) in the auth branch.
- A sign-in page and `POST` endpoint for the password method. Passwords hashed with Argon2id (19 MiB, t=2) as PHC strings, re-hashed at sign-in when parameters change; concurrent verifications capped. Policy: 15 to 256 characters, refused if in a bundled list of the 10 000 most common, no composition rule, no expiry.
- Failed sign-ins slow down with a growing delay per account and per IP; never a permanent lockout. Unknown account and wrong password take the same time.
- The session cookie carries only the signed session id, `__Host-` prefixed over HTTPS, HttpOnly, SameSite=Lax. A session ends after 12 h idle or 7 days (settings), enforced server-side. Sign-out revokes the session; "sign out everywhere" revokes all of the account's sessions; changing the password revokes the others.
- With no sign-in method configured, the password method is enabled with no account. While no Admin exists, HARP logs a setup link: a single-use invitation to the Admin role, valid 72 h, regenerated at each boot while unused. Nobody signs in before it is accepted. Proxied traffic is never blocked.
- State-changing routes rely on the CSRF guard of #1324.

**Out of scope**

Invitations for other accounts, tokens, OIDC (later children).
