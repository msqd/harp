"""Guards that shipped code only imports distributions ``[project.dependencies]`` declares.

An import that resolves only through a parent dependency (``click`` via ``rich-click``) breaks the user's install the
day the parent restructures, and CI never notices. The scanned files are the ones the wheel ships (Hatchling's own
selection, so ``tests/``, ``conftest.py`` and ``node_modules`` are out), minus the cookiecutter template, which is the
generated project's code and has its own dependencies.
"""

import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

from tests.utils.declared_imports import (
    declared_distributions,
    imported_distributions,
    shipped_python_files,
    undeclared_imports,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Imported by shipped code and deliberately not declared. Each entry states why.
DELIBERATELY_UNDECLARED = {
    # pydantic requires an exact pydantic-core version, so it always comes with pydantic; our own range would only
    # duplicate that pin and conflict on every pydantic bump.
    "pydantic-core",
    # Dev-only, guarded by `try/except ImportError` (harp/views/json.py).
    "freezegun",
    # Development environment only (`harp start`), gated by check_packages/assert_package_is_available.
    "honcho",
}


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source)
    return path


def test_imports_are_mapped_to_their_distribution(tmp_path):
    path = _write(tmp_path, "mod.py", "import click\nfrom pydantic_core import to_json\n")
    mapping = {"click": ["click"], "pydantic_core": ["pydantic-core"]}

    assert imported_distributions([path], mapping) == {"click": {path}, "pydantic-core": {path}}


def test_stdlib_first_party_and_relative_imports_are_ignored(tmp_path):
    path = _write(tmp_path, "mod.py", "import os\nimport harp\nfrom harp_apps import proxy\nfrom . import sibling\n")

    assert imported_distributions([path], {}) == {}


def test_imports_inside_functions_count(tmp_path):
    path = _write(tmp_path, "mod.py", "def f():\n    import click\n")

    assert imported_distributions([path], {"click": ["click"]}) == {"click": {path}}


def test_declared_distributions_are_normalized_and_stripped_of_extras_and_bounds():
    declared = declared_distributions(["Rich_Click>=1.9,<1.10", "sqlalchemy[asyncio]>=2.0", "httpx"])

    assert declared == {"rich-click", "sqlalchemy", "httpx"}


def test_undeclared_import_is_reported_by_name(tmp_path):
    path = _write(tmp_path, "mod.py", "import click\nimport httpx\n")
    mapping = {"click": ["click"], "httpx": ["httpx"]}

    undeclared = undeclared_imports([path], {"httpx"}, mapping)

    assert set(undeclared) == {"click"}
    assert undeclared["click"] == {path}


def test_shipped_files_exclude_tests_node_modules_and_cookiecutters():
    files = {str(path.relative_to(REPO_ROOT)) for path in shipped_python_files(REPO_ROOT)}

    assert "harp/config/asdict.py" in files
    assert not any("/tests/" in f or f.endswith("conftest.py") or "node_modules" in f for f in files)
    assert not any(f.startswith("harp/commandline/cookiecutters/") for f in files)


def test_shipped_code_imports_only_declared_distributions():
    if not (REPO_ROOT / "pyproject.toml").exists():
        pytest.skip("not a source checkout")
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]

    undeclared = undeclared_imports(
        shipped_python_files(REPO_ROOT),
        declared_distributions(project["dependencies"]) | DELIBERATELY_UNDECLARED,
        packages_distributions(),
    )

    assert not undeclared, "shipped code imports distributions missing from [project.dependencies]: " + ", ".join(
        f"{dist} (e.g. {sorted(paths)[0].relative_to(REPO_ROOT)})" for dist, paths in sorted(undeclared.items())
    )
