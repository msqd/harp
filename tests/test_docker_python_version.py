"""Keep Docker's default interpreter installable for this package."""

import re
import tomllib
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("dockerfile", ["Dockerfile", "Dockerfile.pypi"])
def test_default_docker_python_matches_project_requirement(dockerfile):
    requirement = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]
    content = (ROOT / dockerfile).read_text()
    match = re.search(r"^ARG PYTHON_VERSION=(\d+\.\d+)$", content, re.MULTILINE)
    assert match is not None, f"{dockerfile} needs a default Python version"
    assert match.group(1) in SpecifierSet(requirement), (
        f"{dockerfile} defaults to Python {match.group(1)}, outside requires-python {requirement}"
    )
