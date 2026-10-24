"""Which Docker tags a release pushes: ``bin/docker_tags.py``."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("docker_tags", ROOT / "bin" / "docker_tags.py")
docker_tags = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docker_tags)

GIT_TAGS = ["0.9.0-rc1", "0.10.0", "0.11.0", "0.11.1", "0.12.0", "not-a-version"]


def names(version, git_tags=GIT_TAGS):
    return docker_tags.docker_tags(version, git_tags)


def test_highest_release_moves_every_tag():
    assert names("0.12.0") == ["0.12.0", "0.12", "0", "latest"]


def test_patch_on_older_line_keeps_latest_and_major():
    assert names("0.11.1") == ["0.11.1", "0.11"]


def test_highest_release_of_an_older_major_moves_its_major_only():
    assert names("0.12.0", [*GIT_TAGS, "1.0.0"]) == ["0.12.0", "0.12", "0"]


def test_versions_compare_numerically_not_as_text():
    assert names("0.10.1", ["0.9.0", "0.10.0", "0.10.1"]) == ["0.10.1", "0.10", "0", "latest"]


def test_prerelease_only_gets_its_exact_tag():
    assert names("0.13.0-rc1", [*GIT_TAGS, "0.13.0-rc1"]) == ["0.13.0-rc1"]


def test_prereleases_do_not_count_as_highest_stable():
    assert names("0.12.1", [*GIT_TAGS, "0.13.0-rc1"]) == ["0.12.1", "0.12", "0", "latest"]


def test_images_are_named_for_both_registries():
    assert docker_tags.images("0.11.1", GIT_TAGS, "msqd/harp") == [
        "ghcr.io/msqd/harp:0.11.1",
        "makersquad/harp-proxy:0.11.1",
        "ghcr.io/msqd/harp:0.11",
        "makersquad/harp-proxy:0.11",
    ]
