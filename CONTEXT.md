# HARP

An API runtime proxy. Traffic passes through it on the way to an origin, and HARP caches what it may
reuse, records what passed through for the operator to inspect, and applies the operator's rules on the
way.

## Language

### The two stores

HARP holds two stores of HTTP messages. They look alike and exist for opposite reasons, which is the
distinction most often got wrong.

**Cache**:
A store of responses kept in order to answer a later request without going to the origin. Reuse is what
makes it a cache, and it is why RFC 9111 binds it.
_Avoid_: storage, response store

**Transaction Record**:
What HARP persists about traffic that passed through it, for an operator to inspect. Nothing in it is
ever read back into a response. Best-effort by design: under load, storage sheds transactions and
message detail rather than slowing traffic down.
_Avoid_: audit trail, log, history

**Transaction**:
One exchange through the proxy: a request, the response it received, and what HARP did in between.
_Avoid_: call, hit, event

**Message**:
One half of a transaction, a request or a response, as recorded. Carries a summary and, unless
suppressed, its headers and body.

### Recording

**Payload**:
The headers and body of a message. The part that can be suppressed, as distinct from the fact that the
message existed.

**Suppression**:
Deliberately not recording a payload, at the request of the caller or the origin. Distinct from
shedding, and the two must be distinguishable in the record.
_Avoid_: skipping, filtering

**Shedding**:
Dropping transactions or message detail because storage is under pressure. Not a decision about the
traffic, and never a promise to anyone.
_Avoid_: throttling, sampling

**Marker**:
A string attached to a transaction that carries a decision about it, which storage and other
applications may act on. The vocabulary in which such decisions are expressed.

### Roles

**Caller**:
The client that sent the request to HARP. In HARP's intended deployment it is an application the
operator controls, which is why its stated intent carries weight.
_Avoid_: client, consumer, user

**Origin**:
The upstream service HARP forwards to. A third party. It may protect its own response payload and may
not erase the record of what was asked of it.
_Avoid_: backend, upstream, remote, server

**Operator**:
Whoever runs this HARP instance. Accountable for what the proxy does, and therefore able to override
any default. See [ADR-0001](./docs/adr/0001-compliant-by-default-operator-may-override.md).
_Avoid_: admin, user, owner

**Endpoint**:
A named upstream configured on the proxy, which requests are routed to. Names a destination, not a URL
path.
_Avoid_: route, service, target

## Decisions

Architecture decision records live in [`docs/adr/`](./docs/adr/).
