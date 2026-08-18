"""
Reading cache-tests results, and comparing a run against a recorded baseline.

The suite emits one verdict per test id: ``true`` for a pass, or a ``[kind, message]`` pair for a
failure. It emits no aggregate, and this module deliberately does not invent one to compare against.
Comparison is **per test id**, because an aggregate cannot tell a regression from upstream changing
the suite, and a gate that cannot say which thing broke is a gate somebody switches off.

Only the pass or fail of a verdict is compared. The failure message is upstream's prose and may be
reworded without anything changing on our side.
"""

from dataclasses import dataclass
from json import JSONDecodeError, loads
from pathlib import Path
from typing import Mapping, NamedTuple, Sequence


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


@dataclass(frozen=True)
class Comparison:
    #: Passed in the baseline, failed in every run.
    regressions: tuple[str, ...]
    #: Failed in the baseline, passed in every run.
    improvements: tuple[str, ...]
    #: Verdict differs between runs, so neither direction is claimed.
    flaky: tuple[str, ...]
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


def _as_verdicts(document, source) -> dict[str, bool]:
    if not isinstance(document, Mapping):
        raise UnusableResults(f"{source} should be a mapping of test id to verdict, got {type(document).__name__}")

    verdicts = {}
    for test_id, verdict in document.items():
        if verdict is True:
            verdicts[test_id] = True
        elif verdict is False or isinstance(verdict, (list, tuple)):
            verdicts[test_id] = False
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
    )


def score(results: Mapping[str, bool]) -> Score:
    return Score(sum(1 for passed in results.values() if passed), len(results))


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

    regressions, improvements, flaky = [], [], []
    for test_id in sorted(observed.intersection(baseline)):
        verdicts = {run[test_id] for run in runs}
        if len(verdicts) > 1:
            flaky.append(test_id)
            continue
        passes = verdicts.pop()
        if baseline[test_id] and not passes:
            regressions.append(test_id)
        elif passes and not baseline[test_id]:
            improvements.append(test_id)

    return Comparison(
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        flaky=tuple(flaky),
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


def render(baseline: Baseline, runs: Sequence[Mapping[str, bool]], *, backend: str) -> str:
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
        f"  recorded {baseline.recorded_on} on {baseline.backend} at {baseline.harp_commit}",
        "",
    ]

    verb = "regressions" if comparison.confirmed else "regressions (unconfirmed, single run)"
    lines += [
        f"  {verb}: {len(comparison.regressions)}",
        f"  improvements: {len(comparison.improvements)}",
        f"  flaky, verdict differed between runs: {len(comparison.flaky)}",
        f"  added upstream since the baseline: {len(comparison.added)}",
        f"  removed upstream since the baseline: {len(comparison.removed)}",
        "",
    ]

    lines += _listing("regressed", comparison.regressions)
    lines += _listing("improved", comparison.improvements)
    lines += _listing("flaky", comparison.flaky)
    lines += _listing("added upstream", comparison.added)
    lines += _listing("removed upstream", comparison.removed)

    if comparison.improvements and not comparison.regressions:
        lines += [
            "",
            "  This run passes tests the baseline does not. Re-record it deliberately if it is real:",
            "    make test-e2e-cache-baseline REASON='...'",
        ]

    return "\n".join(lines)
