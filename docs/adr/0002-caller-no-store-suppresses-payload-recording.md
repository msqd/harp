# ADR-0002: A caller's `no-store` suppresses payload recording, but not the record that traffic happened

- **Status**: accepted, not yet implemented
- **Date**: 2026-08-17
- **Decided in**: [#927](https://github.com/msqd/harp/issues/927)

**This decision applies from 0.11 and is not implemented in 0.10.** What 0.10 does is described below
under *Rejected*, as "Recording everything, as 0.10 does". Read this record as what was decided, not as
a description of the release you are running.

A request carrying `Cache-Control: no-store` has its headers and bodies left out of the transaction
record, in both directions. The transaction row and the message rows still exist, carrying the URL,
method, status and timing. An origin sending `no-store` on its response suppresses that response's
headers and body only.

This reverses what shipped in 0.10, which honoured the directive in the cache and recorded everything
regardless. See [#927](https://github.com/msqd/harp/issues/927).

## Why the RFC does not decide this

RFC 9111 §5.2.1.5 binds a *cache*, and §1 defines a cache as a store that exists "to reduce the response
time and network bandwidth consumption on future equivalent requests". HARP's transaction record never
serves anything back into a response, so the specification is **silent** about it.

That cuts both ways, and it is the reason this ADR exists: honouring the directive here is not compliance,
and declining to is not a violation. Neither position may claim the RFC. It is a product decision, decided
on the merits below.

## The merits

**The caller knows what it is carrying, per request.** In the deployment HARP is built for, an egress
proxy in front of third-party APIs, the calling application is the operator's own. It knows which of its
requests hold a secret, and it knows per request rather than per endpoint. Requiring the operator to
enumerate sensitive endpoints in rules is brittle and goes stale.

**The record of *what happened* is not the caller's to erase.** Suppressing the payload is not the same
as suppressing the fact of the call. A caller cannot make itself invisible: the transaction still appears
with its URL, status and timing, so an operator can always see what passed through their proxy and when.
This is what makes honouring the directive safe rather than an evasion mechanism.

**The origin is not the caller.** An origin's `no-store` suppresses its own response payload and nothing
else. It cannot suppress the request, because the request is evidence of what we asked it for, and the
origin is a third party rather than a component the operator controls. An origin that could erase the
request would be able to hide its own interface from the people integrating with it.

## Rejected

**Suppressing the transaction entirely.** Would let any caller remove its traffic from the record by
setting a header. The record exists to show operators what crossed their proxy; a caller-controlled
deletion inverts who it is for.

**Recording everything, as 0.10 does.** Defensible, and it was our answer until this discussion. It leans
on the record being an audit trail, which it is not: under load, storage sheds transactions and message
detail rather than applying backpressure ([#945](https://github.com/msqd/harp/issues/945)). An argument
from completeness cannot be made by a store that is not complete.

**Stripping the query string from the summary while keeping the path.** Arbitrary. A secret sits in a path
segment as easily as in a query parameter, so this protects one shape of mistake and not the other while
looking like a solution. Redaction is a real feature and gets its own design.

**A configuration setting to turn the behaviour off.** Rejected for now under
[ADR-0001](./0001-compliant-by-default-operator-may-override.md): the override belongs with the markers
that already express storage decisions, not in a second mechanism that says a similar thing differently.

## Consequences

**There is currently no way for an operator to override this**, and that is a gap rather than a guarantee.
The intended mechanism is the transaction markers, which already express exactly this vocabulary
(`skip-request-body-storage` and its siblings). Until that exists, the documentation says HARP does not
*currently* provide an override. It must not say that none is possible: under
[ADR-0001](./0001-compliant-by-default-operator-may-override.md), one is owed.

**A suppressed payload must be distinguishable from a lost one.** An empty payload panel already means
several things, including that storage shed it under pressure. The intended mechanism is two persisted
booleans, `x_no_store_request` and `x_no_store_response`, recording that a directive caused the
suppression rather than that storage failed. They describe what was dropped rather than who asked for it,
which is the distinction that matters when someone is looking at an empty panel and wondering whether HARP
lost their data. Neither exists yet; both arrive with the implementation.

**Redaction remains unsolved and is now more visible.** The message summary carries the request method,
path and query string, with no scheme or host, and nothing on the transaction path is masked. A caller
sending `no-store` on a request whose path or query holds a credential still has that credential stored.
This is true today and is not made worse by this decision, but this decision will make people expect
otherwise.
