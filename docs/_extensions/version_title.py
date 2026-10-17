"""Docs title and "Edit on GitHub" branch, computed from the version built and the release tags."""

import re
import subprocess
import tomllib
from pathlib import Path
from typing import NamedTuple

from packaging.version import InvalidVersion, Version

RELEASE_TAG = re.compile(r"^\d+\.\d+\.\d+$")


class DocsVersion(NamedTuple):
    title: str
    source_branch: str


def release_lines(tags: list[str]) -> list[tuple[int, int]]:
    """Version lines (major, minor) having a final release tag, highest first."""
    lines = {tuple(map(int, tag.split(".")[:2])) for tag in tags if RELEASE_TAG.match(tag)}
    return sorted(lines, reverse=True)


def project_version(root: Path) -> str:
    """Version declared in ``pyproject.toml`` (the git-describe version of ``harp`` is not usable here)."""
    return tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]


def git_tags(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "tag", "--list"], cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return out.stdout.split()


def docs_version(package_version: str, tags: list[str], rtd_slug: str | None = None) -> DocsVersion:
    """Title version and source branch for the package version being built.

    ``rtd_slug`` is ``READTHEDOCS_VERSION``; ``latest`` always builds ``main``.
    """
    try:
        parsed = Version(package_version)
    except InvalidVersion:
        return DocsVersion(package_version, "main")

    line = (parsed.major, parsed.minor)
    name = f"{line[0]}.{line[1]}"
    lines = release_lines(tags)

    if parsed.is_devrelease and (not lines or line > lines[0]):
        role = "next"
    elif lines and line == lines[0]:
        role = "stable"
    elif len(lines) > 1 and line == lines[1]:
        role = "oldstable"
    else:
        role = None

    is_main = rtd_slug == "latest" or (rtd_slug is None and parsed.is_devrelease)
    return DocsVersion(f"{name} ({role})" if role else name, "main" if is_main else name)
