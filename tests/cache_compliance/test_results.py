"""
Unit tests for the cache-tests result reader and baseline comparison.

The comparison is what decides whether ``make test-e2e-cache`` passes, so it is tested on its own,
away from a running proxy. Every test here describes a situation the gate has to survive: upstream
adding or removing tests, a run flapping, a baseline recorded on another storage backend.
"""

import json
from dataclasses import replace

import pytest

from tests.cache_compliance.results import (
    Baseline,
    UnusableResults,
    compare,
    load_baseline,
    load_run,
    render,
    score,
)


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


class TestLoadRun:
    def test_reads_the_suite_verdicts_as_booleans(self, tmp_path):
        path = write(tmp_path, "run.json", {"a": True, "b": ["Assertion", "nope"], "c": ["Setup", "retry"]})

        assert load_run(path) == {"a": True, "b": False, "c": False}

    def test_refuses_an_empty_result_set(self, tmp_path):
        """A run that produced no verdicts is a run that did not happen."""
        path = write(tmp_path, "run.json", {})

        with pytest.raises(UnusableResults, match="no verdicts"):
            load_run(path)

    def test_refuses_something_that_is_not_json(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text("Cache Tests Complete\n")

        with pytest.raises(UnusableResults, match="not valid json"):
            load_run(path)

    def test_refuses_a_json_document_that_is_not_a_mapping(self, tmp_path):
        path = write(tmp_path, "run.json", ["a", "b"])

        with pytest.raises(UnusableResults, match="mapping"):
            load_run(path)

    def test_refuses_a_verdict_it_cannot_interpret(self, tmp_path):
        path = write(tmp_path, "run.json", {"a": True, "b": 42})

        with pytest.raises(UnusableResults, match="b"):
            load_run(path)

    def test_refuses_a_missing_file(self, tmp_path):
        with pytest.raises(UnusableResults, match="no such file"):
            load_run(tmp_path / "absent.json")


class TestScore:
    def test_counts_passing_verdicts(self):
        assert score({"a": True, "b": False, "c": True}) == (2, 3)

    def test_percentage_is_of_the_total(self):
        assert score({"a": True, "b": False, "c": True, "d": False}).percent == 50.0


class TestCompare:
    def test_a_test_that_passed_and_now_fails_is_a_regression(self):
        comparison = compare({"a": True}, [{"a": False}])

        assert comparison.regressions == ("a",)

    def test_a_test_that_failed_and_now_passes_is_an_improvement(self):
        comparison = compare({"a": False}, [{"a": True}])

        assert comparison.improvements == ("a",)
        assert comparison.regressions == ()

    def test_a_test_that_failed_and_still_fails_is_nothing_at_all(self):
        """The suite's usual state: 158 of 365 fail in the baseline and fail again, and none of that is news."""
        comparison = compare({"a": False}, [{"a": False}])

        assert comparison.improvements == ()
        assert comparison.regressions == ()
        assert comparison.flaky == ()

    def test_a_test_that_passed_and_still_passes_is_nothing_at_all(self):
        comparison = compare({"a": True}, [{"a": True}])

        assert comparison.improvements == ()
        assert comparison.regressions == ()

    def test_counts_hold_together_over_a_mixed_run(self):
        """An improvement count that exceeds the change in score means the comparison is miscounting."""
        baseline = {"stays": True, "breaks": True, "fixed": False, "still_broken": False}
        run = {"stays": True, "breaks": False, "fixed": True, "still_broken": False}

        comparison = compare(baseline, [run])

        assert comparison.regressions == ("breaks",)
        assert comparison.improvements == ("fixed",)
        assert score(run).passed - score(baseline).passed == len(comparison.improvements) - len(comparison.regressions)

    def test_a_test_upstream_added_is_not_a_regression_however_it_fares(self):
        """Upstream growing the suite must never fire the gate, which is why we compare per test id."""
        comparison = compare({"a": True}, [{"a": True, "new": False}])

        assert comparison.added == ("new",)
        assert comparison.regressions == ()

    def test_a_test_upstream_removed_is_not_a_regression(self):
        comparison = compare({"a": True, "gone": True}, [{"a": True}])

        assert comparison.removed == ("gone",)
        assert comparison.regressions == ()

    def test_a_test_failing_in_only_one_of_two_runs_is_flaky_not_a_regression(self):
        """Measured: one test in 365 flaps on a 502, which would fire a single-run gate on an unchanged commit."""
        comparison = compare({"a": True}, [{"a": True}, {"a": False}])

        assert comparison.flaky == ("a",)
        assert comparison.regressions == ()

    def test_a_test_failing_in_both_runs_is_a_confirmed_regression(self):
        comparison = compare({"a": True}, [{"a": False}, {"a": False}])

        assert comparison.regressions == ("a",)
        assert comparison.flaky == ()

    def test_an_improvement_must_also_hold_across_every_run(self):
        comparison = compare({"a": False}, [{"a": True}, {"a": False}])

        assert comparison.improvements == ()
        assert comparison.flaky == ("a",)

    def test_a_single_run_leaves_regressions_unconfirmed(self):
        assert compare({"a": True}, [{"a": False}]).confirmed is False

    def test_two_runs_confirm(self):
        assert compare({"a": True}, [{"a": False}, {"a": False}]).confirmed is True

    def test_regressions_are_reported_in_a_stable_order(self):
        comparison = compare({"z": True, "a": True}, [{"z": False, "a": False}])

        assert comparison.regressions == ("a", "z")

    def test_comparing_against_no_run_at_all_is_refused(self):
        with pytest.raises(UnusableResults, match="no run"):
            compare({"a": True}, [])


class TestLoadBaseline:
    def test_reads_conditions_and_verdicts(self, tmp_path):
        path = write(
            tmp_path,
            "baseline.json",
            {
                "conditions": {
                    "backend": "postgresql",
                    "suite_commit": "be694001",
                    "harp_commit": "ac5811fb",
                },
                "recorded_on": "2026-08-18",
                "reason": "first recorded run, see #990",
                "results": {"a": True, "b": False},
            },
        )

        baseline = load_baseline(path)

        assert baseline.backend == "postgresql"
        assert baseline.suite_commit == "be694001"
        assert baseline.recorded_on == "2026-08-18"
        assert baseline.results == {"a": True, "b": False}

    def test_refuses_a_baseline_without_a_backend(self, tmp_path):
        """A baseline that does not say what it was measured on cannot be compared against anything."""
        path = write(tmp_path, "baseline.json", {"conditions": {}, "results": {"a": True}})

        with pytest.raises(UnusableResults, match="backend"):
            load_baseline(path)

    def test_refuses_a_baseline_with_no_verdicts(self, tmp_path):
        path = write(tmp_path, "baseline.json", {"conditions": {"backend": "sqlite"}, "results": {}})

        with pytest.raises(UnusableResults, match="no verdicts"):
            load_baseline(path)


class TestRender:
    def baseline(self):
        return Baseline(
            backend="postgresql",
            suite_commit="be694001",
            harp_commit="ac5811fb",
            recorded_on="2026-08-18",
            reason="first recorded run",
            results={"a": True, "b": False},
        )

    def test_states_the_storage_backend_of_the_run_next_to_the_score(self):
        """The same suite on two backends is two measurements, so a score without its backend is not a result."""
        report = render(self.baseline(), [{"a": True, "b": False}], backend="postgresql")

        assert "storage backend    postgresql" in report
        assert "1/2" in report

    def test_labels_the_baseline_with_the_backend_the_baseline_was_recorded_on(self):
        """Not with the run's, which would quietly relabel a baseline as something it is not."""
        baseline = replace(self.baseline(), backend="sqlite")

        report = render(baseline, [{"a": True, "b": False}], backend="postgresql")

        assert "storage backend    postgresql" in report
        assert "recorded 2026-08-18 on sqlite" in report

    def test_names_the_tests_that_regressed(self):
        report = render(self.baseline(), [{"a": False, "b": False}, {"a": False, "b": False}], backend="postgresql")

        assert "a" in report
        assert "regression" in report.lower()

    def test_says_a_single_run_has_not_confirmed_anything(self):
        report = render(self.baseline(), [{"a": False, "b": False}], backend="postgresql")

        assert "unconfirmed" in report.lower()

    def test_reports_improvements_even_when_nothing_regressed(self):
        report = render(self.baseline(), [{"a": True, "b": True}], backend="postgresql")

        assert "improvement" in report.lower()
        assert "b" in report
