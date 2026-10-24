"""Scheduled report of upper bounds that exclude the latest PyPI release: the logic behind ``bin/check_upper_bounds``."""

import importlib.util
import re
from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("check_upper_bounds", ROOT / "bin" / "check_upper_bounds.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

PYPROJECT = {
    "project": {
        "name": "harp-proxy",
        "dependencies": ["pydantic>=2.12,<2.13", "Click>=8.1,<9", "packaging>=23.2"],
        "optional-dependencies": {"mysql": ["cryptography>=50.0,<51"]},
    },
    "dependency-groups": {"dev": ["harp-proxy[mysql]", "pytest>=7.4.3,<9", {"include-group": "other"}]},
}


def test_every_direct_dependency_is_checked_except_the_project_itself():
    names = {requirement.name for requirement in check.direct_requirements(PYPROJECT)}

    assert names == {"pydantic", "Click", "packaging", "cryptography", "pytest"}


def test_cap_below_latest_release_is_reported():
    latest = {"pydantic": "2.14.1", "Click": "8.3.0", "packaging": "25.0", "cryptography": "50.1", "pytest": "9.0.1"}

    found = check.excluding_latest(check.direct_requirements(PYPROJECT), lambda name: Version(latest[name]))

    assert [(r.name, str(v)) for r, v in found] == [("pydantic", "2.14.1"), ("pytest", "9.0.1")]


def test_nothing_is_reported_when_caps_hold_the_latest_release():
    latest = {"pydantic": "2.12.5", "Click": "8.3.0", "packaging": "25.0", "cryptography": "50.1", "pytest": "8.4"}

    found = check.excluding_latest(check.direct_requirements(PYPROJECT), lambda name: Version(latest[name]))

    assert found == []


def test_latest_release_ignores_prereleases_and_yanked_files():
    payload = {
        "releases": {
            "1.0": [{"yanked": False}],
            "2.0": [{"yanked": True}],
            "3.0rc1": [{"yanked": False}],
            "0.9": [],
        }
    }

    assert check.latest_release(payload) == Version("1.0")


def test_report_names_each_cap_and_latest_release():
    requirement = check.direct_requirements({"project": {"dependencies": ["pydantic>=2.12,<2.13"]}})[0]

    report = check.render([(requirement, Version("2.14.1"))])

    assert "pydantic" in report and "<2.13" in report and "2.14.1" in report


def test_main_fails_and_summarizes_when_a_cap_excludes_latest(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\ndependencies = ["pydantic>=2.12,<2.13"]\n')
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    payload = {"releases": {"2.14.1": [{"yanked": False}]}}

    status = check.main(pyproject, fetch=lambda name: payload)

    assert status == 1
    assert "pydantic" in summary.read_text()


def test_main_passes_when_no_cap_excludes_latest(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\ndependencies = ["pydantic>=2.12,<3"]\n')
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    payload = {"releases": {"2.14.1": [{"yanked": False}]}}

    assert check.main(pyproject, fetch=lambda name: payload) == 0


WORKFLOW = (ROOT / ".github" / "workflows" / "upper-bounds.yml").read_text()


def test_workflow_runs_on_schedule_only_with_read_permission():
    assert re.search(r"^on:\n  schedule:\n", WORKFLOW, re.M)
    assert "push:" not in WORKFLOW and "pull_request" not in WORKFLOW
    assert re.search(r"^permissions:\n  contents: read\n", WORKFLOW, re.M)
    assert "write" not in WORKFLOW


def test_workflow_actions_are_pinned_to_a_sha():
    uses = re.findall(r"uses: (\S+)", WORKFLOW)

    assert uses and all(re.search(r"@[0-9a-f]{40}$", u) for u in uses)
