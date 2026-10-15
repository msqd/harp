"""The documentation build renders pending changelog fragments as the "unreleased" page."""

from pathlib import Path

import pytest

from docs._extensions.pending_changelog import render_pending_changelog, upcoming_version

TEMPLATE = Path(__file__).parent.parent / "docs" / "changelogs" / "towncrier.rst.j2"

TOWNCRIER = f"""
[tool.towncrier]
directory = "changelog.d"
template = "{TEMPLATE}"
title_format = false
issue_format = "#{{issue}}"

[[tool.towncrier.type]]
directory = "fixed"
name = "Fixed"
showcontent = true
"""


def make_repo(root: Path, version: str, fragments: dict[str, str]) -> Path:
    (root / "changelog.d").mkdir()
    (root / "docs" / "changelogs").mkdir(parents=True)
    (root / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n{TOWNCRIER}')
    (root / "changelog.d" / "README.rst").write_text("readme\n")
    for name, text in fragments.items():
        (root / "changelog.d" / name).write_text(text)
    return root


@pytest.mark.parametrize(
    "declared,expected",
    [("0.11.0.dev0", "0.11.0"), ("0.11.0-alpha1", "0.11.0"), ("0.11.0", "0.11.0")],
)
def test_upcoming_version_read_from_pyproject(tmp_path, declared, expected):
    make_repo(tmp_path, declared, {})
    assert upcoming_version(tmp_path) == expected


def test_pending_page_titled_with_upcoming_version(tmp_path):
    make_repo(tmp_path, "0.11.0.dev0", {"1.fixed.rst": "Fixed a thing.\n"})
    assert render_pending_changelog(tmp_path) is True
    page = (tmp_path / "docs" / "changelogs" / "unreleased.rst").read_text()
    assert page.startswith("Version 0.11.0 (unreleased)\n")
    assert "Fixed a thing." in page
    assert (tmp_path / "docs" / "changelogs" / "_unreleased_toctree.inc").read_text().strip() != ""


def test_no_fragment_means_no_unreleased_page(tmp_path):
    make_repo(tmp_path, "0.11.0.dev0", {})
    stale = tmp_path / "docs" / "changelogs" / "unreleased.rst"
    stale.write_text("stale")
    assert render_pending_changelog(tmp_path) is False
    assert not stale.exists()
    assert (tmp_path / "docs" / "changelogs" / "_unreleased_toctree.inc").read_text().strip() == ""
