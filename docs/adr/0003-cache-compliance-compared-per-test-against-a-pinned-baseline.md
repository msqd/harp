# ADR-0003: RFC 9111 compliance is compared per test id against a baseline pinned to its storage backend

- **Status**: accepted
- **Date**: 2026-08-18
- **Decided in**: [#990](https://github.com/msqd/harp/issues/990)

`make test-e2e-cache` runs the [cache-tests](https://github.com/http-tests/cache-tests) suite against
HARP and fails when a test that passed in a recorded baseline fails **in two consecutive runs**.

Comparison is per test id, never on the score. Baselines are recorded per storage backend, and a run
is never compared against a baseline from another backend. Moving a baseline is a separate command
that records a reason.

## What was actually being decided

The suite emits 365 verdicts and no aggregate. The score is something we compute. So "detect a
regression" had an obvious shape that turned out to be the wrong one, and naming why is the point of
this record.

**Comparing the score cannot distinguish a regression from upstream churn.** 207/365 against 205/362
is consistent with two tests regressing, with three tests being deleted and two added, and with any
mixture. A gate that fires on that number cannot say what broke, and a gate that cannot say what broke
is one somebody switches off after the second false alarm. That costs us the times it was right.

Comparing per test id dissolves the ambiguity, and the four cases fall out of it: a test that passed
and now fails is a regression; a test upstream removed is not; a test upstream added is not, however
it fares; a test that now passes is an improvement. Upstream can add thirty hard tests, drop the
percentage by eight points, and fire nothing.

## Why two runs and not one

Measured on `ac5811fb`, five full runs of the suite against an unchanged HARP: **two tests of 365
change verdict between runs**, both failing with `Setup, Response 1 status is 502, not 200`. HARP
intermittently fails to proxy a request and the test never starts.

One of those runs would have reported a regression on an unchanged commit. A per-test gate with no
confirmation step therefore fires spuriously roughly one run in four, which is the failure mode above
wearing a different hat.

**Requiring the failure in two consecutive runs was preferred to a list of known-flaky test ids.** A
list needs curating, goes stale silently, and grows until it covers the thing that actually broke. The
second run costs about a minute, happens only when the first one found something, and needs nobody to
maintain it.

The cost is accepted and named: a regression that is *itself* intermittent is classified as flaky and
does not fail the gate. It is printed in the report under `flaky` rather than swallowed.

## Why the baseline never moves by itself

A gate that re-baselines when it sees an improvement will absorb a flapping test on the run where it
passes, and then fire on that test forever after. Re-baselining is therefore a separate command,
`make test-e2e-cache-baseline REASON='...'`, and the reason is stored next to the numbers.

The reporting side is deliberately not symmetric with the failing side: improvements are counted and
listed on every run, including runs that pass. A gate that only ever reports bad news gets read as
noise, and the improvement count is what tells somebody a re-baseline is worth doing.

## Why baselines are pinned to a storage backend

The same suite on two storage backends is two different measurements. Measured on the same commit:

| storage | score |
|---|---|
| PostgreSQL | 207/365 (56.7%) |
| SQLite, file-backed | 207/365 (56.7%) |
| SQLite, `:memory:?cache=shared` | 146/365 (40.0%), then 140/365 (38.4%) |

So the gate **refuses to compare** a run against a baseline recorded on another backend, rather than
reporting a 61-test difference that says nothing about HARP. A refusal is the honest output when the
conditions of a measurement are not the conditions of the thing it is being compared to.

The default backend is file-backed SQLite, which needs nothing installed and reproduces the
PostgreSQL score. **Release validation runs against PostgreSQL**, because that is the production path
and because SQLite does not enforce column widths: a 40-character `blobs.id` reached the 0.10 release
candidate precisely because every instrument pointed at it was pointed at SQLite.

## Rejected

**Failing on any score drop.** The shape most people reach for first. Fires on upstream suite changes,
cannot explain itself when it does, and gets switched off. See above.

**Failing only when the run does not complete.** Safe, and tells us nothing about regressions, which is
most of the reason to run the suite at all. Kept as *part* of the answer rather than the whole of it:
a failure to run is a hard failure, checked separately and first, and it never reports a score.

**Comparing failure messages as well as pass or fail.** The messages are upstream's prose and can be
reworded without anything changing on our side. Only the verdict is compared.

**A list of known-flaky test ids.** See above.

**Running the suite on HARP's default `:memory:` storage.** It is the zero-setup option and it looked
like the obvious default, but the cache mostly does not store anything under it, so the run measures
the storage defect rather than the cache. That defect is real and is being tracked separately; it is
not something a compliance baseline should be built on top of.

## Consequences

**A quiet defect became visible, and more will.** While the target could not run, nothing behind it
had ever been observed. The `:memory:` behaviour in the table above is the first thing the working
instrument found, on its first day. Expect the same shape again: what this suite reports now was
previously unobservable rather than absent.

**The intermittent 502 is now measured rather than suspected.** Two tests of 365 per run, which is
what the confirmation step exists to absorb. If that rate climbs, the flaky count in the report climbs
with it and stays visible, but nothing fails on it: this record does not decide what an acceptable
flap rate is.

**Two baselines have to be kept.** A change that moves the score has to re-record both, on both
backends, or the untouched one becomes wrong. Nothing enforces that today beyond the backend label
printed next to every score.
