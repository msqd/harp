"""
Tests for the command line the make target actually calls.

Exit codes are the contract between this and ``run-tests.sh``: 0 nothing regressed, 1 something did,
2 the run cannot be trusted enough to say either way.
"""

import json

from tests.cache_compliance.__main__ import CANNOT_COMPARE, OK, REGRESSED, main

BASELINE = {
    "conditions": {"backend": "sqlite", "suite_commit": "be694001", "harp_commit": "ac5811fb"},
    "recorded_on": "2026-08-18",
    "reason": "first recorded run, see #990",
    "results": {"a": True, "b": True, "c": False},
}


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


def baseline_file(tmp_path, payload=None):
    return write(tmp_path, "baseline.json", payload or BASELINE)


class TestCheck:
    def test_exits_ok_when_the_run_matches_the_baseline(self, tmp_path, capsys):
        run = write(tmp_path, "run.json", {"a": True, "b": True, "c": ["Assertion", "nope"]})

        assert main(["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(run)]) == OK

    def test_exits_regressed_when_a_previously_passing_test_fails(self, tmp_path):
        run = write(tmp_path, "run.json", {"a": True, "b": ["Assertion", "nope"], "c": False})

        code = main(["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(run)])

        assert code == REGRESSED

    def test_two_runs_disagreeing_is_not_a_regression(self, tmp_path):
        """The measured flap: one run in four fails a test on a transient 502."""
        first = write(tmp_path, "first.json", {"a": True, "b": True, "c": False})
        second = write(tmp_path, "second.json", {"a": True, "b": ["Setup", "502"], "c": False})

        code = main(
            ["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(first), str(second)]
        )

        assert code == OK

    def test_two_runs_agreeing_is_a_regression(self, tmp_path):
        first = write(tmp_path, "first.json", {"a": True, "b": ["Setup", "502"], "c": False})
        second = write(tmp_path, "second.json", {"a": True, "b": ["Setup", "502"], "c": False})

        code = main(
            ["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(first), str(second)]
        )

        assert code == REGRESSED

    def test_refuses_to_compare_a_run_against_a_baseline_from_another_backend(self, tmp_path, capsys):
        """SQLite and PostgreSQL differ by 61 tests here, so this comparison would be pure noise."""
        run = write(tmp_path, "run.json", {"a": True, "b": True, "c": False})

        code = main(["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "postgresql", str(run)])

        assert code == CANNOT_COMPARE
        output = capsys.readouterr().out
        assert "postgresql" in output and "sqlite" in output

    def test_refuses_a_run_that_produced_nothing(self, tmp_path, capsys):
        run = write(tmp_path, "run.json", {})

        code = main(["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(run)])

        assert code == CANNOT_COMPARE
        assert "nothing ran" in capsys.readouterr().out

    def test_states_the_score_and_the_backend(self, tmp_path, capsys):
        run = write(tmp_path, "run.json", {"a": True, "b": True, "c": False})

        main(["check", "--baseline", str(baseline_file(tmp_path)), "--backend", "sqlite", str(run)])

        output = capsys.readouterr().out
        assert "2/3" in output
        assert "storage backend    sqlite" in output

    def test_never_writes_the_baseline_even_when_the_run_improves_on_it(self, tmp_path, capsys):
        """Re-baselining is a deliberate act. A gate that absorbs an improvement absorbs a flap with it."""
        path = baseline_file(tmp_path)
        before = path.read_text()
        run = write(tmp_path, "run.json", {"a": True, "b": True, "c": True})

        assert main(["check", "--baseline", str(path), "--backend", "sqlite", str(run)]) == OK

        # it saw the improvement and said so, and still left the baseline alone
        output = capsys.readouterr().out
        assert "improvements: 1" in output
        assert "\n    c\n" in output
        assert path.read_text() == before


class TestRecord:
    def record(self, tmp_path, path, *runs, backend="postgresql", reason="cache rewrite landed"):
        return main(
            [
                "record",
                "--baseline",
                str(path),
                "--backend",
                backend,
                "--suite-commit",
                "be694001",
                "--harp-commit",
                "ac5811fb",
                "--recorded-on",
                "2026-08-18",
                "--reason",
                reason,
                *[str(r) for r in runs],
            ]
        )

    def test_a_test_that_moved_while_recording_is_recorded_as_failing(self, tmp_path):
        """
        The safe side. A baseline is a claim about what reliably passes, so a test nobody could
        observe passing twice must not be able to produce a regression later.
        """
        first = write(tmp_path, "first.json", {"steady": True, "moved": True})
        second = write(tmp_path, "second.json", {"steady": True, "moved": ["Setup", "502"]})
        path = tmp_path / "new-baseline.json"

        assert self.record(tmp_path, path, first, second) == OK

        written = json.loads(path.read_text())
        assert written["results"] == {"steady": True, "moved": False}

    def test_records_how_many_runs_back_the_baseline(self, tmp_path):
        """A baseline from one observation cannot represent a population that moves, so it says so."""
        first = write(tmp_path, "first.json", {"a": True})
        second = write(tmp_path, "second.json", {"a": True})
        path = tmp_path / "new-baseline.json"

        self.record(tmp_path, path, first, second)

        assert json.loads(path.read_text())["conditions"]["runs"] == 2

    def test_reports_what_moved_while_recording(self, tmp_path, capsys):
        first = write(tmp_path, "first.json", {"steady": True, "moved": True})
        second = write(tmp_path, "second.json", {"steady": True, "moved": ["Setup", "502"]})

        self.record(tmp_path, tmp_path / "b.json", first, second)

        output = capsys.readouterr().out
        assert "moved" in output
        assert "1" in output

    def test_only_records_tests_every_run_observed(self, tmp_path):
        """A test missing from one run was not measured that time, so it is not in the baseline."""
        first = write(tmp_path, "first.json", {"a": True, "only-in-first": True})
        second = write(tmp_path, "second.json", {"a": True})

        self.record(tmp_path, tmp_path / "b.json", first, second)

        assert json.loads((tmp_path / "b.json").read_text())["results"] == {"a": True}

    def test_writes_a_baseline_carrying_its_conditions_and_its_reason(self, tmp_path):
        run = write(tmp_path, "run.json", {"a": True, "b": ["Assertion", "nope"]})
        path = tmp_path / "new-baseline.json"

        code = main(
            [
                "record",
                "--baseline",
                str(path),
                "--backend",
                "postgresql",
                "--suite-commit",
                "be694001",
                "--harp-commit",
                "ac5811fb",
                "--recorded-on",
                "2026-08-18",
                "--reason",
                "cache rewrite landed",
                str(run),
            ]
        )

        assert code == OK
        written = json.loads(path.read_text())
        assert written["conditions"] == {
            "backend": "postgresql",
            "suite_commit": "be694001",
            "harp_commit": "ac5811fb",
            "runs": 1,
        }
        assert written["reason"] == "cache rewrite landed"
        assert written["recorded_on"] == "2026-08-18"
        assert written["results"] == {"a": True, "b": False}

    def test_refuses_to_record_a_run_that_produced_nothing(self, tmp_path, capsys):
        run = write(tmp_path, "run.json", {})
        path = tmp_path / "new-baseline.json"

        code = main(
            [
                "record",
                "--baseline",
                str(path),
                "--backend",
                "sqlite",
                "--suite-commit",
                "be694001",
                "--harp-commit",
                "ac5811fb",
                "--reason",
                "nope",
                str(run),
            ]
        )

        assert code == CANNOT_COMPARE
        assert not path.exists()
