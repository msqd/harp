# auth: OpenID Connect providers and identity linking

**Problem**

Teams that already have Google, GitHub, Keycloak or Entra want single sign-on rather than another password.

**Acceptance criteria**

- Settings declare any number of named OIDC providers by issuer (discovery), client id and secret; each is a sign-in method enabled explicitly.
- Authorization code flow with PKCE S256, single-use `state` and `nonce`, one callback URL per provider, `iss` checked against mix-up (RFC 9207), `Referrer-Policy: no-referrer` on the callback.
- An OIDC identity is keyed on `(issuer, sub)`; renaming a provider in the settings orphans nothing. Email never identifies.
- Signing in through a provider with no matching identity is refused: accounts come from invitations only.
- From its own session, an account links another identity, after re-authenticating when the session is older than 15 minutes. It may remove any identity but its last; an Admin may remove any. Removing an identity revokes the sessions it opened. Disabling a provider suspends its identities without deleting them.

**Out of scope**

Group or claim mapping to roles; creating accounts at first sign-in.
