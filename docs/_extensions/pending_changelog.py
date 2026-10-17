"""Renders the pending changelog fragments as the "unreleased" changelog page (generated, git-ignored)."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path


def upcoming_version(root: Path) -> str:
    """The version the pending fragments will ship in: `pyproject.toml` version without its pre-release suffix."""
    declared = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    return re.match(r"\d+(\.\d+)*", declared).group(0)


def has_fragments(root: Path) -> bool:
    return any(p.name != "README.rst" for p in (root / "changelog.d").glob("*.rst"))


def render_pending_changelog(root: Path) -> bool:
    """Writes `docs/changelogs/unreleased.rst` and the toctree entry listing it, or neither if nothing is pending."""
    changelogs = root / "docs" / "changelogs"
    page, toctree = changelogs / "unreleased.rst", changelogs / "_unreleased_toctree.inc"
    page.unlink(missing_ok=True)
    toctree.write_text("")
    if not has_fragments(root):
        return False

    body = subprocess.run(
        [
            sys.executable,
            "-m",
            "towncrier",
            "build",
            "--draft",
            "--version",
            upcoming_version(root),
            "--date",
            "unreleased",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    page.write_text(body + "\n")
    toctree.write_text(".. toctree::\n    :maxdepth: 1\n\n    unreleased\n")
    return True
