#!/usr/bin/env python3
"""
List the direct dependencies whose version range excludes the latest PyPI release.

Reads ``[project.dependencies]``, the extras and the dependency groups of ``pyproject.toml``. A cap that excludes the
latest release is a decision to revisit (its comment in ``pyproject.toml`` says why it exists), or a bound that drifted
unnoticed. Prints a Markdown report, appends it to ``$GITHUB_STEP_SUMMARY`` when set, and exits 1 when the list is not
empty. It never edits ``pyproject.toml``.

Usage:
    python bin/check_upper_bounds.py [pyproject.toml]
"""

import json
import os
import sys
import tomllib
import urllib.request
from collections.abc import Callable
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

PROJECT = "harp-proxy"


def direct_requirements(pyproject: dict) -> list[Requirement]:
    """Every requirement the file declares, minus the project itself (dev groups depend on it for its extras)."""
    project = pyproject.get("project", {})
    lines = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        lines.extend(extra)
    for group in pyproject.get("dependency-groups", {}).values():
        lines.extend(item for item in group if isinstance(item, str))
    requirements = (Requirement(line) for line in lines)
    return [r for r in requirements if canonicalize_name(r.name) != PROJECT]


def latest_release(payload: dict) -> Version:
    """Highest final version of a PyPI JSON payload that still has a non-yanked file."""
    versions = []
    for name, files in payload["releases"].items():
        try:
            version = Version(name)
        except InvalidVersion:
            continue
        if not version.is_prerelease and any(not f.get("yanked") for f in files):
            versions.append(version)
    return max(versions)


def excluding_latest(
    requirements: list[Requirement], latest: Callable[[str], Version]
) -> list[tuple[Requirement, Version]]:
    found = []
    for requirement in requirements:
        version = latest(requirement.name)
        if not requirement.specifier.contains(version):
            found.append((requirement, version))
    return found


def render(found: list[tuple[Requirement, Version]]) -> str:
    if not found:
        return "No upper bound excludes the latest PyPI release.\n"
    lines = [
        "## Upper bounds that exclude the latest PyPI release",
        "",
        "| Dependency | Range | Latest |",
        "|---|---|---|",
    ]
    lines.extend(f"| {r.name} | `{r.specifier}` | {version} |" for r, version in found)
    return "\n".join(lines) + "\n"


def fetch_pypi(name: str) -> dict:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{canonicalize_name(name)}/json", timeout=30) as response:
        return json.load(response)


def main(pyproject: Path, fetch: Callable[[str], dict] = fetch_pypi) -> int:
    requirements = direct_requirements(tomllib.loads(pyproject.read_text()))
    found = excluding_latest(requirements, lambda name: latest_release(fetch(name)))
    report = render(found)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as stream:
            stream.write(report)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "pyproject.toml")))
