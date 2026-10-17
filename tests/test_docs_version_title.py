"""The docs title names the version line and its role, computed from the version and the release tags."""

import pytest

from docs._extensions.version_title import docs_version, project_version, release_lines

TAGS = ["0.9.0", "0.10.0", "0.10.1", "0.11.0", "0.11.0-rc1", "0.12.0-alpha1", "0.11.0-3-gabc"]


@pytest.mark.parametrize(
    "package_version, slug, title, branch",
    [
        ("0.12.0.dev0", "latest", "0.12 (next)", "main"),
        ("0.11.0", "stable", "0.11 (stable)", "0.11"),
        ("0.11.1.dev0", "0.11", "0.11 (stable)", "0.11"),
        ("0.10.1", "0.10", "0.10 (oldstable)", "0.10"),
        ("0.9.1", "0.9", "0.9", "0.9"),
        ("0.12.0.dev0", None, "0.12 (next)", "main"),
        ("0.11.0", None, "0.11 (stable)", "0.11"),
    ],
)
def test_title_and_branch(package_version, slug, title, branch):
    assert docs_version(package_version, TAGS, slug) == (title, branch)


def test_after_new_minor_release_the_previous_line_is_oldstable():
    tags = [*TAGS, "0.12.0"]
    assert docs_version("0.11.1", tags, "0.11").title == "0.11 (oldstable)"
    assert docs_version("0.12.0", tags, "stable").title == "0.12 (stable)"
    assert docs_version("0.13.0.dev0", tags, "latest").title == "0.13 (next)"
    assert docs_version("0.10.1", tags, "0.10").title == "0.10"


def test_without_tags_a_release_has_no_role():
    assert docs_version("0.11.0", [], None).title == "0.11"


def test_project_version_is_read_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.12.0.dev0"\n')
    assert project_version(tmp_path) == "0.12.0.dev0"


def test_only_final_release_tags_count():
    assert release_lines(TAGS) == [(0, 11), (0, 10), (0, 9)]
