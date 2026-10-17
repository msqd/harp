"""Metadata recorded in every benchmark result, so numbers stay attributable."""

import json
import os
import platform
import subprocess
from pathlib import Path

from harp._native import active

CPUINFO = Path("/proc/cpuinfo")


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short=10", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_dirty(cwd: Path | None = None) -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=cwd
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return "true" if status.strip() else "false"


def native() -> str:
    return os.environ.get("HARP_NATIVE") or "none"


def native_active() -> str:
    return json.dumps(active(), sort_keys=True)


def cpu_model(cpuinfo: Path = CPUINFO) -> str:
    try:
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


def python_build() -> str:
    return " ".join((platform.python_implementation(), platform.python_version(), *platform.python_build()))


def collect() -> dict[str, str]:
    return {
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "harp_native": native(),
        "harp_native_active": native_active(),
        "cpu_model": cpu_model(),
        "python_build": python_build(),
    }
