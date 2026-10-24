# ADR-0010: HARP's own credentials never reach an origin, and no setting changes that

- **Status**: proposed
- **Date**: 2026-10-24
- **Decided in**: [explore/auth](https://github.com/msqd/harp/milestone/24)

**Proposed on the explore/auth exploration branch; nothing of it is implemented.**

Before forwarding a request to an origin, the proxy removes HARP's own credentials from it: the
dashboard session cookie, and any `Authorization: Bearer` value that is a HARP token (recognised by its
`harp_` prefix and its checksum). The removal is recorded on the transaction with a marker. No setting
turns it off.

## Why the proxy sees them at all

A cookie is scoped to a host, not to a port. A browser that signed in to the dashboard on
`harp.internal:4080` sends the same cookie to `harp.internal:4000`, a proxy port, on every request an
application in that browser makes through it. A HARP token pasted into the wrong `Authorization` header
by a caller travels the same way. Without the strip, an origin, which is a third party, receives a
credential that lets it act on HARP as that account.

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
