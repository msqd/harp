#!/usr/bin/env python3
"""
Check that a docker image ships exactly what ``uv.lock`` pins.

Compares the distributions installed in the image with ``uv export --no-dev`` for the extras the image installs.
The image has no pip, so its packages are listed with ``importlib.metadata``.

Usage:
    python bin/check_docker_lock.py export > dist/constraints.txt   # what the Dockerfile installs with -c
    python bin/check_docker_lock.py check <image>
"""

import subprocess
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

EXTRAS = ("postgresql", "sentry")
PROJECT = "harp-proxy"

LIST_INSTALLED = (
    "import importlib.metadata as m; [print(d.metadata['Name'] + '==' + d.version) for d in m.distributions()]"
)


def parse_requirements(text: str) -> dict[str, str]:
    """Pinned `name==version` lines to {canonical name: version}, skipping markers that do not apply here."""
    pins = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate():
            pins[canonicalize_name(requirement.name)] = next(iter(requirement.specifier)).version
    return pins


def differences(locked: dict[str, str], installed: dict[str, str]) -> list[str]:
    installed = {name: version for name, version in installed.items() if name != PROJECT}
    problems = []
    for name in sorted(locked.keys() | installed.keys()):
        if name not in installed:
            problems.append(f"{name}: lock {locked[name]}, image missing")
        elif name not in locked:
            problems.append(f"{name}: not in lock, image {installed[name]}")
        elif locked[name] != installed[name]:
            problems.append(f"{name}: lock {locked[name]}, image {installed[name]}")
    return problems


def run(*command: str) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def export_lock() -> str:
    command = ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes", "--no-annotate"]
    for extra in EXTRAS:
        command += ["--extra", extra]
    return run(*command)


def check(image: str) -> int:
    locked = parse_requirements(export_lock())
    installed = parse_requirements(run("docker", "run", "--rm", "--entrypoint", "python", image, "-c", LIST_INSTALLED))
    problems = differences(locked, installed)
    if problems:
        print(f"{image} does not match uv.lock:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    print(f"ok: {image} ships the {len(locked)} packages pinned by uv.lock")
    return 0


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["export"]:
            print(export_lock(), end="")
        case ["check", image]:
            sys.exit(check(image))
        case _:
            sys.exit(__doc__)
