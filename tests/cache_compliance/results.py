"""
Reading cache-tests results, and comparing a run against a recorded baseline.

The suite emits one verdict per test id: ``true`` for a pass, or a ``[kind, message]`` pair for a
failure. It emits no aggregate, and this module deliberately does not invent one to compare against.
Comparison is **per test id**, because an aggregate cannot tell a regression from upstream changing
the suite, and a gate that cannot say which thing broke is a gate somebody switches off.

Only the pass or fail of a verdict is compared. The failure message is upstream's prose and may be
reworded without anything changing on our side.
"""

import re
from dataclasses import dataclass
from enum import Enum
from json import JSONDecodeError, loads
from pathlib import Path
from typing import Mapping, NamedTuple, Sequence

#: Statuses HARP returns when its own proxying failed, from harp_apps/proxy/constants.py. A verdict
#: reporting one of these as the status it actually got describes HARP failing to reach the origin,
#: not the cache behaving wrongly.
HARP_PROXY_ERROR_STATUSES = frozenset({"500", "502", "503", "504", "526"})

#: The suite reports a status mismatch as "status is <actual>, not <expected>". Matching on the
#: actual side is what keeps `status-502-fresh` and its siblings out of this: a test that asked for a
#: 502 and did not get one reports the 502 on the *expected* side. It also cannot match a header
#: comparison at all, which is a third category that exists (`cdn-date-update-exceed`).
_STATUS_MISMATCH = re.compile(r"status is (\d{3}), not (\d{3})")


class Verdict(Enum):
    """What one run of one test tells us."""

    PASSED = "passed"
    FAILED = "failed"
    #: HARP failed to serve the request, so the test never reached the cache and says nothing.
    UNOBSERVED = "unobserved"

    @property
    def passed(self) -> bool:
        return self is Verdict.PASSED


def is_unobserved(verdict) -> bool:
    """
    Whether this verdict describes HARP failing to proxy rather than the cache behaving wrongly.

    HARP emits roughly fourteen proxy errors per suite run, measured on both storage backends and on
    0.9.1 as well as 0.10. When one lands on a test's setup request the test never ran, and calling
    that a compliance failure is a category error.

    **This is the only place the gate reads upstream's prose**, so it is deliberately narrow and
    fails safe: anything it does not recognise is treated as a real failure, which costs a
    confirmation run rather than silence. ``tests/cache_compliance/test_unobserved.py`` pins what it
    must and must not match against a whole recorded run.
    """
    if not isinstance(verdict, (list, tuple)) or len(verdict) < 2:
        return False
    match = _STATUS_MISMATCH.search(str(verdict[1]))
    if not match:
        return False
    actual, expected = match.groups()
    return actual in HARP_PROXY_ERROR_STATUSES and actual != expected


class UnusableResults(Exception):
    """
    Raised when results or a baseline cannot be trusted enough to compare.

    An instrument that cannot trust its conditions refuses to report, rather than reporting anyway: a
    number produced under conditions nobody chose looks exactly like every other number.
    """


class Score(NamedTuple):
    passed: int
    total: int

    @property
    def percent(self) -> float:
        return 100.0 * self.passed / self.total if self.total else 0.0

    def __str__(self) -> str:
        return f"{self.passed}/{self.total} ({self.percent:.1f}%)"


@dataclass(frozen=True)
class Baseline:
    backend: str
    suite_commit: str
    harp_commit: str
    recorded_on: str
    reason: str
    results: dict[str, bool]
    #: How many suite runs were consolidated into it. One cannot represent a population that moves.
    runs: int = 1


@dataclass(frozen=True)
class Comparison:
    #: Passed in the baseline, failed in every run.
    regressions: tuple[str, ...]
    #: Failed in the baseline, passed in every run.
    improvements: tuple[str, ...]
    #: Verdict differs between runs, so neither direction is claimed.
    flaky: tuple[str, ...]
    #: HARP failed to serve the request in at least one run, so the test was never measured.
    unobserved: tuple[str, ...]
    #: Present in the runs, absent from the baseline. Upstream grew the suite.
    added: tuple[str, ...]
    #: Present in the baseline, absent from every run. Upstream shrank the suite.
    removed: tuple[str, ...]
    #: True once more than one run agrees, which is what makes a regression a claim rather than a candidate.
    confirmed: bool


def _read_json(path: Path):
    try:
        raw = Path(path).read_text()
    except FileNotFoundError as exc:
        raise UnusableResults(f"no such file: {path}") from exc
    try:
        return loads(raw)
    except JSONDecodeError as exc:
        raise UnusableResults(f"{path} is not valid json: {exc}") from exc


def _as_verdicts(document, source) -> dict[str, Verdict]:
    if not isinstance(document, Mapping):
        raise UnusableResults(f"{source} should be a mapping of test id to verdict, got {type(document).__name__}")

    verdicts = {}
    for test_id, verdict in document.items():
        if verdict is True:
            verdicts[test_id] = Verdict.PASSED
        elif verdict is False or isinstance(verdict, (list, tuple)):
            verdicts[test_id] = Verdict.UNOBSERVED if is_unobserved(verdict) else Verdict.FAILED
        else:
            raise UnusableResults(f"{source} has an uninterpretable verdict for {test_id!r}: {verdict!r}")

    if not verdicts:
        raise UnusableResults(f"{source} contains no verdicts, so nothing ran")

    return verdicts


def load_run(path: Path) -> dict[str, bool]:
    """Read one cache-tests run, as written by ``npm run cli``."""
    return _as_verdicts(_read_json(path), path)


def load_baseline(path: Path) -> Baseline:
    """Read a recorded baseline, along with the conditions it was measured under."""
    document = _read_json(path)
    if not isinstance(document, Mapping):
        raise UnusableResults(f"{path} should be a mapping, got {type(document).__name__}")

    conditions = document.get("conditions") or {}
    backend = conditions.get("backend")
    if not backend:
        raise UnusableResults(f"{path} does not say which storage backend it was measured on")

    return Baseline(
        backend=backend,
        suite_commit=conditions.get("suite_commit", "unknown"),
        harp_commit=conditions.get("harp_commit", "unknown"),
        recorded_on=document.get("recorded_on", "unknown"),
        reason=document.get("reason", ""),
        results=_as_verdicts(document.get("results"), path),
        runs=conditions.get("runs", 1),
    )


def _verdict(value) -> Verdict:
    """Accept a Verdict, or a plain bool for the many places that only care about pass or fail."""
    if isinstance(value, Verdict):
        return value
    return Verdict.PASSED if value else Verdict.FAILED


def score(results: Mapping[str, object]) -> Score:
    return Score(sum(1 for value in results.values() if _verdict(value).passed), len(results))


def consolidate(runs: Sequence[Mapping[str, bool]]) -> tuple[dict[str, bool], tuple[str, ...]]:
    """
    Reduce several runs of the suite to the verdicts a baseline should record.

    A test is recorded as passing only if it passed in **every** run. A test that moved while it
    was being recorded lands on ``False``, which is the safe side: it can then produce a spurious
    *improvement* later, which costs nothing, but never a spurious regression.

    This exists because a baseline taken from a single run cannot represent a population that
    moves, and this suite's does: measured over eight runs per backend, roughly one test per run
    changes verdict, and it is a different test each time.

    Returns the verdicts and the ids that moved, so the recording can say what it saw.
    """
    if not runs:
        raise UnusableResults("no run to record as a baseline")

    observed = sorted(set(runs[0]).intersection(*(set(run) for run in runs)))
    results = {test_id: all(_verdict(run[test_id]).passed for run in runs) for test_id in observed}
    moved = tuple(test_id for test_id in observed if len({_verdict(run[test_id]).passed for run in runs}) > 1)
    return results, moved


def compare(baseline: Mapping[str, bool], runs: Sequence[Mapping[str, bool]]) -> Comparison:
    """
    Compare one or more runs against a baseline, test id by test id.

    A verdict has to hold across *every* run to be claimed in either direction. With a single run
    that is trivially true and the result is a candidate; with two it is confirmed. This is what
    absorbs the suite's measured flap without anybody maintaining a list of known-flaky ids.
    """
    if not runs:
        raise UnusableResults("no run to compare against the baseline")

    observed = set(runs[0]).intersection(*(set(run) for run in runs)) if len(runs) > 1 else set(runs[0])
    seen_anywhere = set().union(*(set(run) for run in runs))

    regressions, improvements, flaky, unobserved = [], [], [], []
    for test_id in sorted(observed.intersection(baseline)):
        verdicts = [_verdict(run[test_id]) for run in runs]

        # A test HARP failed to serve was never measured, so it is evidence for nothing. Claiming a
        # regression from it would be claiming the cache misbehaved on a request the cache never saw.
        if any(v is Verdict.UNOBSERVED for v in verdicts):
            unobserved.append(test_id)
            continue

        outcomes = {v.passed for v in verdicts}
        if len(outcomes) > 1:
            flaky.append(test_id)
            continue
        passes = outcomes.pop()
        if _verdict(baseline[test_id]).passed and not passes:
            regressions.append(test_id)
        elif passes and not _verdict(baseline[test_id]).passed:
            improvements.append(test_id)

    return Comparison(
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        flaky=tuple(flaky),
        unobserved=tuple(unobserved),
        added=tuple(sorted(seen_anywhere - set(baseline))),
        removed=tuple(sorted(set(baseline) - seen_anywhere)),
        confirmed=len(runs) > 1,
    )


def _listing(label: str, test_ids: Sequence[str], limit: int = 20) -> list[str]:
    if not test_ids:
        return []
    shown = list(test_ids[:limit])
    lines = [f"  {label}:"] + [f"    {test_id}" for test_id in shown]
    if len(test_ids) > limit:
        lines.append(f"    ... and {len(test_ids) - limit} more")
    return lines


def render(
    baseline: Baseline,
    runs: Sequence[Mapping[str, object]],
    *,
    backend: str,
    harp_errors: int | None = None,
) -> str:
    """
    Render the report a human reads in the terminal.

    The backend sits next to the score because the same suite on two storage backends is two
    different measurements, and a score quoted without its conditions gets quoted again without them.
    """
    comparison = compare(baseline.results, runs)
    scores = " then ".join(str(score(run)) for run in runs)

    lines = [
        "RFC 9111 compliance, http-tests/cache-tests",
        "",
        f"  storage backend    {backend}",
        f"  suite commit       {baseline.suite_commit}",
        f"  runs               {len(runs)}",
        f"  score              {scores}",
        f"  baseline           {score(baseline.results)}"
        f"  recorded {baseline.recorded_on} on {baseline.backend} at {baseline.harp_commit}"
        f", from {baseline.runs} run{'s' if baseline.runs != 1 else ''}",
        "",
    ]

    verb = "regressions" if comparison.confirmed else "regressions (unconfirmed, single run)"
    lines += [
        f"  {verb}: {len(comparison.regressions)}",
        f"  improvements: {len(comparison.improvements)}",
        f"  flaky, verdict differed between runs: {len(comparison.flaky)}",
        f"  unobserved, HARP failed to serve the request: {len(comparison.unobserved)}",
        f"  added upstream since the baseline: {len(comparison.added)}",
        f"  removed upstream since the baseline: {len(comparison.removed)}",
        "",
    ]

    lines += _listing("regressed", comparison.regressions)
    lines += _listing("improved", comparison.improvements)
    lines += _listing("flaky", comparison.flaky)
    lines += _listing("unobserved", comparison.unobserved)

    # Auditing the one place this gate reads upstream's prose, with a number that does not.
    if harp_errors and not comparison.unobserved:
        lines += [
            "",
            f"  NOTE: HARP logged {harp_errors} failed request(s) but no verdict was recognised as one.",
            "  Either they landed on tests that failed anyway, or the suite reworded its messages and",
            "  the gate can no longer tell a proxy failure from a compliance failure. See",
            "  tests/cache_compliance/test_unobserved.py.",
        ]
    lines += _listing("added upstream", comparison.added)
    lines += _listing("removed upstream", comparison.removed)

    if comparison.improvements and not comparison.regressions:
        lines += [
            "",
            "  This run passes tests the baseline does not. Re-record it deliberately if it is real:",
            "    make test-e2e-cache-baseline REASON='...'",
        ]

    return "\n".join(lines)
