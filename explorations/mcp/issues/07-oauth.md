# mcp: OAuth through an external identity provider

**Problem**

Pasting a token into each MCP client is the only way in. The MCP authorization specification (2025-11-25) expects an OAuth 2.1 resource server, and teams with Keycloak or Entra would rather sign agents in through it.

**Acceptance criteria**

- HARP serves RFC 9728 protected resource metadata for `/mcp`, naming the configured identity provider as authorization server.
- An access token issued by that provider for HARP's audience (RFC 8707) is accepted: signature (JWKS), `iss`, `aud` and `exp` checked; `(iss, sub)` resolves to an existing identity (explore/auth decision 19), and so to its account. No identity, no access. Tokens for another audience are refused.
- Scopes cap the role (`harp:viewer`, `harp:editor`), with the same rule as tokens: effective role is `min(account role, cap)`. The client (`azp`) fills the actor's client.
- The provider setting says whether it accepts access tokens and for which audience.

**Out of scope**

HARP as an authorization server; dynamic client registration on HARP's side.
