"""
A verdict lost to one of HARP's own proxy errors is unobserved, not failed.

HARP emits about fourteen proxy errors per suite run, measured on both storage backends and on
0.9.1 as well as 0.10. When one lands on a test's setup request, that test never reached the cache,
so the suite's verdict says nothing about compliance. Counting it as a failure is a category error,
and it is the single largest source of false regression candidates.

This is the one place the gate reads upstream's failure prose, so these tests pin exactly what the
pattern must and must not match, including verdicts observed in real runs.
"""

import json
from pathlib import Path

import pytest

from tests.cache_compliance.results import Baseline, Verdict, is_unobserved, load_run, render

BASELINES = Path(__file__).parents[2] / "misc" / "cache-tests" / "baselines"
FIXTURE = Path(__file__).parent / "fixtures" / "recorded-run-sqlite.json"


class TestIsUnobserved:
    @pytest.mark.parametrize(
        "message",
        [
            "Response 1 status is 502, not 200",
            "Response 2 status is 500, not 200",
            "Response 3 status is 503, not 200",
            "Response 1 status is 504, not 304",
        ],
    )
    def test_a_status_harp_itself_returns_on_a_proxy_error_means_the_test_never_ran(self, message):
        assert is_unobserved(["Setup", message]) is True

    @pytest.mark.parametrize(
        "message",
        [
            # The origin was asked for a 502 and HARP served it: this is the test working.
            "Response 2 status is 502, not 502",
            # A cache miss. Real behaviour, and the second largest source of movers.
            "Response 2 does not come from cache",
            "Response 3 does not come from cache",
            # A header comparison. Observed as a mover, and nothing to do with a proxy error.
            'Response 2 header Date is "Mon, 18 Aug 2026 09:38:35 GMT", not "Mon, 18 Aug 2026 09:38:30 GMT"',
            'Response 2 header Content-Length is "null", not "36"',
            # A status mismatch that is not one of HARP's proxy error codes.
            "Response 2 status is 200, not 304",
            "Response 2 status is 404, not 200",
            # The suite gave up for its own reasons.
            "retry",
        ],
    )
    def test_anything_else_is_a_real_verdict(self, message):
        assert is_unobserved(["Setup", message]) is False

    def test_a_pass_is_not_unobserved(self):
        assert is_unobserved(True) is False

    def test_an_unrecognisable_verdict_is_treated_as_a_real_failure(self):
        """Failing safe: if upstream rewords, the gate falls back to fail-twice rather than to silence."""
        assert is_unobserved(["Assertion", "some wording nobody has seen before"]) is False
        assert is_unobserved(["Assertion"]) is False
        assert is_unobserved(False) is False


class TestAgainstProseNobodyHereWrote:
    """
    The committed baselines record pass or fail and no messages, deliberately, so they cannot pin
    this. ``fixtures/recorded-run-sqlite.json`` is a whole real run kept for exactly that: it is the
    only place in the suite where the gate's reading of upstream prose meets prose upstream wrote.

    If a suite update rewords these messages, the fixture goes stale rather than lying, and the live
    cross-check in ``run-tests.sh`` is what notices at runtime: HARP counts its own proxy errors, so
    a run where HARP logged them and the gate recognised none says the pattern stopped matching.
    """

    def run(self):
        return json.loads((FIXTURE).read_text())

    def test_the_fixture_is_a_whole_recorded_run(self):
        assert len(self.run()) == 365

    def test_it_recognises_the_proxy_errors_upstream_actually_reported(self):
        unobserved = [test_id for test_id, verdict in self.run().items() if is_unobserved(verdict)]

        assert "headers-store-Transfer-Encoding" in unobserved, "the deterministic 502, present in every run"
        assert len(unobserved) == 3

    def test_it_leaves_the_cache_misses_alone(self):
        """The other half of the movers. These are real behaviour and must stay comparable."""
        misses = [
            test_id
            for test_id, verdict in self.run().items()
            if isinstance(verdict, list) and "does not come from cache" in str(verdict[1])
        ]

        assert misses, "the fixture should contain cache misses, they are half the flap"
        assert not any(is_unobserved(self.run()[test_id]) for test_id in misses)


class TestTheCommittedBaselines:
    @pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
    def test_states_its_conditions_and_rests_on_enough_runs(self, backend):
        document = json.loads((BASELINES / f"{backend}.json").read_text())

        assert document["conditions"]["backend"] == backend
        assert document["conditions"]["runs"] >= 3, "a baseline from fewer runs cannot represent the measured flap"

    @pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
    def test_loads_as_a_full_set_of_verdicts(self, backend, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(json.loads((BASELINES / f"{backend}.json").read_text())["results"]))

        assert len(load_run(path)) == 365


class TestTheCrossCheck:
    """
    HARP counts its own failed requests. That number is produced by a different instrument from the
    one that reads upstream's prose, so it can catch the prose reader going stale.
    """

    def baseline(self):
        return Baseline(
            backend="sqlite",
            suite_commit="be694001",
            harp_commit="ac5811fb",
            recorded_on="2026-08-18",
            reason="measured",
            results={"a": Verdict.PASSED},
            runs=3,
        )

    def test_says_so_when_harp_failed_requests_but_no_verdict_was_recognised(self):
        """Exactly the shape of an upstream reword: the gate would otherwise report a clean run."""
        report = render(self.baseline(), [{"a": Verdict.PASSED}], backend="sqlite", harp_errors=14)

        assert "no verdict was recognised" in report

    def test_stays_quiet_when_it_did_recognise_one(self):
        report = render(self.baseline(), [{"a": Verdict.UNOBSERVED}], backend="sqlite", harp_errors=14)

        assert "no verdict was recognised" not in report
        assert "unobserved" in report

    def test_stays_quiet_when_harp_failed_nothing(self):
        report = render(self.baseline(), [{"a": Verdict.PASSED}], backend="sqlite", harp_errors=0)

        assert "no verdict was recognised" not in report
