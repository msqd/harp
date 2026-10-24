# proxy: strip HARP's own credentials before the origin

**Problem**

A cookie is scoped to a host, not to a port: a browser signed in to the dashboard sends its session cookie to every proxy port on the same host, and the proxy forwards it to the origin. A HARP token in a caller's `Authorization` header is forwarded the same way. ADR-0010 (branch `explore/auth`) decides HARP always removes them.

**Acceptance criteria**

- Before forwarding, the proxy removes HARP's session cookie from `Cookie` (other cookies kept, header dropped when empty) and an `Authorization: Bearer` whose value is a HARP token (prefix and valid checksum). Test both, and that a non-HARP bearer is forwarded unchanged.
- The removal is recorded on the transaction with a marker.
- No setting disables it.
- The proxy docs state it.

**Out of scope**

Any other header.
