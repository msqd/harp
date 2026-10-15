# ADR-0001: Compliant by default, and the operator may override anything

- **Status**: accepted
- **Date**: 2026-08-17
- **Decided in**: [#927](https://github.com/msqd/harp/issues/927)

Articulated while deciding [#927](https://github.com/msqd/harp/issues/927), but it is not a rule
about caching. It is the general principle the records that follow lean on, and
[ADR-0002](./0002-caller-no-store-suppresses-payload-recording.md) is its first application.

Where a specification permits a choice, HARP takes the safest reading by default, and the operator can
override it. The default is what a careful reader of the spec would expect; the override is what makes
HARP usable in deployments we did not anticipate.

This is already how the project behaves rather than a new rule. `harp_apps/http_cache/settings.py` keeps
`allow_heuristics: False`, declining something RFC 9111 §4.2.2 explicitly permits, because the cache key
is built from the request URL alone and guessing a freshness lifetime would let responses to differently
authenticated callers collide. An operator who wants heuristics turns them on.

## What follows from it

**A conservative default is not a refusal.** If HARP declines to do something a spec allows, there must
be a way for an operator to ask for it. A default that cannot be overridden is a constraint, and a
constraint needs a stronger justification than "this is safer".

**An override that does not exist yet is a gap, not a guarantee.** Where the mechanism has not been built,
say so in those words. Documenting the absence of an override as a promise to the caller creates something
we then have to withdraw, and a withdrawn guarantee costs more than a missing feature.

**The operator outranks the caller, and both outrank our preferences.** A caller can express intent
through the protocol. An operator configures the deployment. Where the two disagree, the operator's
configuration wins, because they are the one accountable for what the proxy does.

## Consequences

Overrides accumulate, and each one is a supported path that has to keep working. That cost is accepted:
the alternative is a proxy that is correct in our deployment and unusable in someone else's.

It also means "the specification says so" is never sufficient on its own. It settles the default. It does
not settle whether an override should exist, which is a product question every time.
