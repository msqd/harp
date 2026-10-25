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

**Cache Entry**:
What the cache keeps for one cache key, a URL on one endpoint: one or more variants.
_Avoid_: cache record, cached item

**Variant**:
One response kept for a cache entry, for one combination of the request headers its `Vary` names.

**Invalidation**:
Removing cache entries because someone decided so: an editor in the dashboard, or a `PURGE` request.
The only way out of the cache that the audit records, when an account decided it.
_Avoid_: purge, flush, eviction

**Expiry**:
A cache entry leaving the cache with no one deciding: its lifetime ran out, or an unsafe request to its
URL made it stale as RFC 9111 requires.
_Avoid_: eviction, invalidation

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

**Redaction**:
Replacing the value of a credential with a placeholder before it is stored, keeping the name it was
sent under. The message is still recorded and the value is visibly replaced, not absent. See
[ADR-0009](./docs/adr/0009-credentials-redacted-before-storage-by-rule.md).
_Avoid_: masking, scrubbing, obfuscation

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
_Avoid_: user, owner

**Endpoint**:
A named upstream configured on the proxy, which requests are routed to. Names a destination, not a URL
path.
_Avoid_: route, service, target

### Access

**Account**:
Something that signs in to HARP and holds a role: a person, or a machine such as a CI job or an
agent. The Operator has an account, but the two are not the same thing.
_Avoid_: user, member, principal

**Sign-in method**:
A way into HARP that the Operator enables: password, one named OpenID Connect provider, token, or
HTTP Basic. Password is enabled when no method is configured. A disabled method lets nobody in,
whatever identities exist for it.

**Identity**:
The link between an account and one sign-in method, such as "Alice, through Google". An account may
have several; a machine account usually has none and signs in with tokens.
_Avoid_: login, credential, provider

**Token**:
A secret that an account hands to a machine so that it can act as that account, with at most that
account's role.
_Avoid_: API key, personal access token

**Invitation**:
An admin's single-use offer of an account with a given role, which expires. The only way an account
for a person comes to exist; the person accepting it chooses the sign-in method.

**Audit Event**:
What an account did to HARP, or what access HARP granted on its own, when, by which means and with
what outcome: a sign-in, a change to someone's access, a manual action on traffic. Never shed,
never edited. Traffic through the proxy belongs to the transaction record, and what HARP does on its
own, such as a breaker opening, to its logs.
_Avoid_: audit log, audit trail, history, journal

**Actor**:
Who did what an audit event records: an account, with the session or token it acted through and the
client it acted from. When nobody could be identified, as in a failed sign-in, only what was
claimed and where from.

**Session**:
One browser signed in to an account through one identity. It ends on its own, at sign-out, or when
an admin or the account revokes it; ending one session leaves the others open.

**Role**:
What a person or machine signed in to HARP may do. One of three, ordered: Viewer, Editor, Admin. Each
includes everything the one below it may do.

**Viewer**:
The role that may read what HARP shows, and act on nothing.

**Editor**:
The role that may also act on traffic, such as invalidating cached responses.

**Admin**:
The role that may also manage who has access and with which role. A role, not the Operator.

## Decisions

Architecture decision records live in [`docs/adr/`](./docs/adr/).
