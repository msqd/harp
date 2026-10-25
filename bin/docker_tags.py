#!/usr/bin/env python3
"""
Docker tags to push for a release.

Every stable release gets ``X.Y.Z`` and ``X.Y``. ``X`` moves only when the release is the highest stable version of
its major, and ``latest`` only when it is the highest stable version published, so a patch on an older line never moves
them backwards. Pre-releases only get their exact tag.

Usage:
    python bin/docker_tags.py <version> <repository> [git tag ...]   # comma separated image names on stdout
"""

import re
import sys

STABLE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
REGISTRIES = ("ghcr.io/{repository}", "makersquad/harp-proxy")


def parse(version: str) -> tuple[int, int, int] | None:
    match = STABLE.match(version)
    return tuple(map(int, match.groups())) if match else None


def docker_tags(version: str, git_tags: list[str]) -> list[str]:
    current = parse(version)
    if current is None:
        return [version]
    stable = [parsed for tag in {*git_tags, version} if (parsed := parse(tag))]
    tags = [version, "{}.{}".format(*current[:2])]
    if current == max(parsed for parsed in stable if parsed[0] == current[0]):
        tags.append(str(current[0]))
    if current == max(stable):
        tags.append("latest")
    return tags


def images(version: str, git_tags: list[str], repository: str) -> list[str]:
    tags = docker_tags(version, git_tags)
    registries = [registry.format(repository=repository) for registry in REGISTRIES]
    return [f"{registry}:{tag}" for tag in tags for registry in registries]


if __name__ == "__main__":
    version, repository, *git_tags = sys.argv[1:]
    print(",".join(images(version, git_tags, repository)))
