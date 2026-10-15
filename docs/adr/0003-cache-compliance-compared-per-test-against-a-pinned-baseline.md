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

## What the flap actually is, measured

Sixteen full runs on `ac5811fb`, eight per backend, cold cache and a fresh HARP each time:

| | SQLite | PostgreSQL |
|---|---|---|
| score range | 206 to 208 of 365 | 206 to 208 of 365 |
| tests that changed verdict at least once | 6 | 4 |
| consecutive run pairs disagreeing on something | 5 of 7 | 5 of 7 |
| HARP proxy errors per run, from its own log | 10 to 11 × 502, 3 × 500 | 10 to 11 × 502, 3 × 500 |

Three things follow, and each one killed a design that looked reasonable before it was measured.

**The mover set does not saturate.** 2 movers at three runs, 4 at four, 6 at eight, still climbing.
Every mover failed *exactly once* in eight runs. This is not a fixed population of flaky tests, it is
a low-rate event landing on a different test each time. **So a baseline that records a measured set of
unstable ids cannot work**, however principled it looks: no finite number of recording runs enumerates
a set that has no boundary.

**The two backends are not meaningfully different.** 6 against 4 is noise, and an earlier reading that
SQLite was the flakier one came from comparing five runs against eight rather than from the backends.
A number that grows with sample size will always look like a difference between two samples of
different size.

**There are two distinct causes, in roughly equal parts.** About half the movers fail as
`Response N status is 502, not 200`, which is HARP failing to proxy: the test never reached the cache.
The other half fail as `Response N does not come from cache`, which is the cache genuinely missing.
They deserve different treatment, and they get it below.

The same measurement against `harp-proxy==0.9.1` shows the 502 rate is inherited and unchanged (11 per
run against 10 to 11), while the 500 rate improved threefold (9 down to 3) and compliance improved by
39 tests. 0.9.1 moved zero times in three runs, but its proxy errors were **deterministic**: ten of
them hit the same ten tests in every run, and not one landed on a test that passes elsewhere. 0.10
loses far fewer verdicts to proxy errors and the ones it loses are no longer always the same tests.

## Why a test HARP failed to serve is unobserved rather than failed

A verdict reporting that the actual status was one of HARP's own proxy error codes describes HARP
failing to reach the origin. **That test never exercised the cache**, so calling it a compliance
failure is a category error, and it was the single largest source of false regression candidates.

Such verdicts are reported under `unobserved` and take no part in the comparison, in either direction.
This is the per-test form of the refusal the gate already performs per run.

**This is the only place the gate reads upstream's prose**, which is a real cost and is mitigated three
ways. It matches on the *actual* status with a *different* status expected, so a test that asked for a
502 and did not get one is untouched, and a header comparison such as `cdn-date-update-exceed` cannot
match at all. It fails safe: anything unrecognised is treated as a real failure, so a reword upstream
costs a confirmation run rather than producing silence. And HARP's own count of failed requests is
passed to the report as a second, independent instrument: a run where HARP logged proxy errors and the
comparison recognised none says so, because that is what an upstream reword would look like.

## Why two runs and not one

Across sixteen runs, **no test failed in two consecutive runs**. A regression therefore has to fail in
two consecutive runs to be claimed, which absorbs the measured flap without anybody maintaining a list.

**Requiring two consecutive failures was preferred to a list of known-flaky test ids.** A list needs
curating, goes stale silently, and grows until it covers the thing that actually broke. The second run
costs about a minute, happens only when the first one found something, and needs nobody to maintain it.

**Raising the bar to three runs was rejected.** It only reduces a probability, at a minute per run, and
the conversation recurs the first time it is not enough.

The cost is accepted and named: **a genuine regression on a test that is also unstable will be
absorbed.** It is visible in the report under `flaky` rather than swallowed, and it is not fatal. A
gate that claims no blind spot is lying; this one has its blind spot measured.

## Why the baseline is recorded from several runs, and never moves by itself

A baseline taken from a single run **cannot represent a population that moves**. Whichever tests
happened to flap during that one run are recorded at their unlucky value and reported for ever after:
the first baseline recorded here had `304-etag-update-response-X-Content-Foo` down as failing, and
every subsequent run reported it as an improvement.

So recording consolidates several runs, three by default, and records a test as passing **only if it
passed in every one**. The baseline becomes the reliable floor rather than one lucky sample, and the
report says how many runs back it, because otherwise a one-run and a three-run baseline read the same.

The asymmetry is the whole argument. A test that moved during recording lands on the *failing* side,
where it can later produce a spurious **improvement** but never a spurious **regression**. **A spurious
improvement is an invitation to look; a spurious regression is a false alarm that gets the gate
switched off.**

A gate that re-baselines when it sees an improvement would absorb a flapping test on the run where it
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

**A baseline that records a measured set of unstable ids.** Derived rather than curated, re-derived on
every re-baseline, and therefore immune to the staleness that condemns a hand-written list. It was the
leading design until the population was measured: the mover set does not saturate, so there is no set
to record. It would have looked principled and quietly excluded the wrong tests.

**Raising the confirmation to three runs.** See above.

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

**A cross-version comparison must read what it installed, not what it is standing next to.** The 0.9.1
figures above were nearly measured against 0.10 three times: `import harp` inside a virtualenv holding
0.9.1 reported `0.10.0-alpha2-211`, because the working directory was the 0.10 checkout and it won on
`sys.path`. Every number would have been wrong, and nothing downstream could have caught it, because
"identical, therefore inherited" is exactly the conclusion such a mistake produces. The check that
caught it was reading `harp.__file__`, not `harp.__version__`. **Read the path, not the version.**

**Two baselines have to be kept.** A change that moves the score has to re-record both, on both
backends, or the untouched one becomes wrong. Nothing enforces that today beyond the backend label
printed next to every score.
