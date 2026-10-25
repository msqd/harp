# ADR-0011: HARP's own credentials never reach an origin, and no setting changes that

- **Status**: proposed
- **Date**: 2026-10-24
- **Decided in**: [explore/auth](https://github.com/msqd/harp/milestone/24)

**Proposed on the explore/auth exploration branch.**

The proxy keeps HARP's own credentials and an origin apart, in both directions:

- **Requests.** Before the request is recorded and forwarded, the proxy removes the dashboard session
  cookie, and any `Authorization: Bearer` value that is a HARP token (recognised by its `harp_` prefix
  and its checksum).
- **Responses.** The proxy removes from an origin's response every `Set-Cookie` whose cookie name is one
  of HARP's session cookie names; other `Set-Cookie` headers are kept.

Either removal is recorded on the transaction with a marker. No setting turns it off.

## Why the proxy sees them at all

A cookie is scoped to a host, not to a port. A browser that signed in to the dashboard on
`harp.internal:4080` sends the same cookie to `harp.internal:4000`, a proxy port, on every request an
application in that browser makes through it. A HARP token pasted into the wrong `Authorization` header
by a caller travels the same way. Without the strip, an origin, which is a third party, receives a
credential that lets it act on HARP as that account.

The same scoping works backwards: an origin answering through a proxy port can send
`Set-Cookie: harp_session=<attacker session>; Path=/`, and the browser applies it to every port of the
host, the dashboard included. The `__Host-` prefix pins a cookie to a host, not to a port, so it does not
help. Dropping that `Set-Cookie` closes the planting.

An origin can also act on HARP with no credential at all: a page it serves through a proxy port can issue
state-changing requests to the dashboard, and `SameSite` ignores ports, so the browser sends the session
cookie along. Stripping credentials does not address that. It is handled by a separate explore/auth issue
requiring same-origin on state-changing dashboard routes, and the documentation recommends serving the
dashboard on a separate hostname.

The MCP authorization specification forbids passing a server's tokens through to an upstream for the
same reason.

## Why this is an exception to ADR-0001

[ADR-0001](./0001-compliant-by-default-operator-may-override.md) lets the operator override any default.
This one has no use the operator could want: HARP's credentials authorise nothing at an origin, and
forwarding them only hands an origin access to HARP. A setting to keep them would exist only to be set by
mistake. The exception is limited to credentials HARP itself issued; every other header, `Authorization`
included, is forwarded as today and stored under the rules of
[ADR-0009](./0009-credentials-redacted-before-storage-by-rule.md).

## Rejected

- **On by default, with an opt-out.** Faithful to ADR-0001, but the opt-out has no legitimate user.
- **Strip the cookie only.** A misplaced `Bearer harp_…` is the caller's mistake, but the cost of the
  mistake falls on the operator's HARP, and the token is recognisable without ambiguity.
- **Rely on `__Host-` cookies.** The prefix pins the cookie to its exact host but not to a port, and it
  requires HTTPS; a dashboard served over plain HTTP on a private network would still leak.
