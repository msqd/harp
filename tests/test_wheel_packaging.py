"""Guards the wheel distribution contents.

Test code and dev-only utilities must not ship in the wheel (they bloat the
distribution and expose internal helpers), while the project scaffolding shipped
by ``harp create project`` — which legitimately contains ``tests/`` and
``conftest.py`` — must be preserved.

These assertions run against Hatchling's own file-selection logic, so they check
the real include/exclude rules from ``pyproject.toml`` without building a wheel
(no network, no frontend build required).
"""

import re
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Matches Python test code and dev-only testing utilities.
TEST_FILE = re.compile(r"(^|/)(tests|testing|__snapshots__)/|(^|/)conftest\.py$|(^|/)test_[^/]*\.py$|_test\.py$")

# The cookiecutter templates ship as production scaffolding; their own tests/ and
# conftest.py belong in the generated user project and must stay in the wheel.
TEMPLATE_PREFIX = "harp/commandline/cookiecutters/"


def _wheel_distribution_paths():
    pytest.importorskip("hatchling.builders.wheel")
    from hatchling.builders.wheel import WheelBuilder

    if not (REPO_ROOT / "pyproject.toml").exists():
        pytest.skip("not a source checkout")

    builder = WheelBuilder(str(REPO_ROOT))
    return {f.distribution_path for f in builder.recurse_included_files()}


def test_wheel_excludes_python_test_code():
    """No test files or testing utilities leak into the wheel (cookiecutter templates aside)."""
    paths = _wheel_distribution_paths()
    leaked = sorted(p for p in paths if p.endswith(".py") and TEST_FILE.search(p) and not p.startswith(TEMPLATE_PREFIX))
    assert leaked == [], f"test code should not ship in the wheel: {leaked}"


def test_wheel_keeps_cookiecutter_template_scaffolding():
    """The generated-project scaffolding (incl. its tests/ and conftest.py) stays shipped."""
    paths = _wheel_distribution_paths()
    template_tests = [
        p for p in paths if p.startswith(TEMPLATE_PREFIX) and ("/tests/" in p or p.endswith("conftest.py"))
    ]
    assert template_tests, "cookiecutter template test scaffolding must remain in the wheel"


def test_wheel_keeps_production_modules():
    """Excluding tests must not drop production code."""
    paths = _wheel_distribution_paths()
    for module in ("harp/__init__.py", "harp/config/__init__.py", "harp_apps/proxy/__init__.py"):
        assert module in paths, f"production module missing from wheel: {module}"


def _force_include_source_dirs():
    """The force-include source directories declared for the sdist and wheel builds."""
    if not (REPO_ROOT / "pyproject.toml").exists():
        pytest.skip("not a source checkout")
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    targets = config["tool"]["hatch"]["build"]["targets"]
    sources = set()
    for target in targets.values():
        sources.update(target.get("force-include", {}).keys())
    return sorted(source for source in sources if (REPO_ROOT / source).is_dir())


def _tracked_files(path: str):
    """Files git tracks under ``path`` — what a fresh clone would actually check out."""
    result = subprocess.run(
        ["git", "ls-files", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_force_include_sources_survive_a_fresh_checkout():
    """Every force-include source must ship a tracked file, or a fresh clone can't build.

    Hatchling resolves force-include paths at build time and raises FileNotFoundError
    when a declared source directory is absent. A directory whose contents are all
    git-ignored vanishes on a fresh checkout, so it must keep at least one tracked
    file (e.g. a .gitkeep) to guarantee the build target always exists.
    """
    sources = _force_include_source_dirs()
    assert sources, "expected at least one force-include source directory to guard"
    missing = [source for source in sources if not _tracked_files(source)]
    assert missing == [], f"force-include sources with no git-tracked file (break fresh clones): {missing}"
