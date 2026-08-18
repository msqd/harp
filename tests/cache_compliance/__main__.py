"""
The command line ``make test-e2e-cache`` calls to turn a cache-tests run into a verdict.

``check`` compares runs against a baseline and returns the gate's answer. ``record`` writes a new
baseline, and exists as a separate command on purpose: re-baselining has to be something somebody
decides and explains, never something the gate does for itself when it sees an improvement. A gate
that absorbs an improvement absorbs a flapping test on the run where it passes, then fires on it
forever.
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

from tests.cache_compliance.results import (
    UnusableResults,
    compare,
    consolidate,
    load_baseline,
    load_run,
    render,
    score,
)

#: Nothing regressed.
OK = 0
#: Something that used to pass now fails, in every run given.
REGRESSED = 1
#: The run or the baseline cannot be trusted enough to say either way, so no number is reported.
CANNOT_COMPARE = 2


def _parser() -> ArgumentParser:
    parser = ArgumentParser(prog="python -m tests.cache_compliance", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="compare runs against a baseline")
    check.add_argument("--baseline", required=True, type=Path)
    check.add_argument("--backend", required=True, help="storage backend the runs were measured on")
    check.add_argument(
        "--harp-errors",
        type=int,
        default=None,
        help="how many requests HARP logged as failed, used to audit the gate's own reading of the verdicts",
    )
    check.add_argument("runs", nargs="+", type=Path, help="one run, or two to confirm a regression")

    record = commands.add_parser("record", help="record a run as the new baseline")
    record.add_argument("--baseline", required=True, type=Path)
    record.add_argument("--backend", required=True)
    record.add_argument("--suite-commit", required=True)
    record.add_argument("--harp-commit", required=True)
    record.add_argument("--recorded-on", default="")
    record.add_argument("--reason", required=True, help="why the baseline is moving, kept next to the numbers")
    record.add_argument("runs", nargs="+", type=Path, help="every run to consolidate into the baseline")

    return parser


def _check(options) -> int:
    baseline = load_baseline(options.baseline)

    if baseline.backend != options.backend:
        print(
            f"Refusing to compare: this run used {options.backend}, the baseline was recorded on "
            f"{baseline.backend}. The same suite on two storage backends is two measurements."
        )
        return CANNOT_COMPARE

    runs = [load_run(path) for path in options.runs]
    print(render(baseline, runs, backend=options.backend, harp_errors=options.harp_errors))

    return REGRESSED if compare(baseline.results, runs).regressions else OK


def _record(options) -> int:
    runs = [load_run(path) for path in options.runs]
    results, moved = consolidate(runs)

    options.baseline.parent.mkdir(parents=True, exist_ok=True)
    options.baseline.write_text(
        json.dumps(
            {
                "conditions": {
                    "backend": options.backend,
                    "suite_commit": options.suite_commit,
                    "harp_commit": options.harp_commit,
                    "runs": len(runs),
                },
                "recorded_on": options.recorded_on,
                "reason": options.reason,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(f"Recorded {score(results)} on {options.backend} from {len(runs)} runs: {options.reason}")
    print(f"  {options.baseline}")
    print(f"  scores seen while recording: {', '.join(str(score(run)) for run in runs)}")
    print(f"  moved while recording, so recorded as failing: {len(moved)}")
    for test_id in moved:
        print(f"    {test_id}")
    return OK


def main(argv=None) -> int:
    options = _parser().parse_args(argv)
    try:
        return _check(options) if options.command == "check" else _record(options)
    except UnusableResults as exc:
        print(f"Refusing to report a number: {exc}")
        return CANNOT_COMPARE


if __name__ == "__main__":
    sys.exit(main())
