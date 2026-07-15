"""Regression tests for running the HARP CLI from a source checkout.

Guards against the class of failure where the ``harp/`` package directory ends
up on ``sys.path`` and shadows a stdlib module (e.g. ``harp/typing`` vs stdlib
``typing``). This happened because ``harp`` had no console entry point, so
``uv run harp ...`` executed the package *directory* instead of a script.

The CLI must import cleanly through the supported invocations: the ``harp``
console script and ``python -m harp`` from the repository root.
"""

import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _console_script(name):
    """Path to an installed console script sitting next to the interpreter."""
    candidate = Path(sys.executable).parent / name
    return candidate if candidate.exists() else None


def test_harp_and_harp_proxy_console_scripts_are_registered():
    names = {ep.name for ep in entry_points(group="console_scripts")}
    assert "harp-proxy" in names, "harp-proxy console script must exist"
    assert "harp" in names, "the 'harp' console script must exist (documented as `harp create project`)"


def test_harp_console_script_runs_without_stdlib_shadow():
    """`harp version` must import and run — this is what `uv run harp` resolves to."""
    harp = _console_script("harp")
    if harp is None:
        pytest.skip("harp console script not installed in this environment")
    result = subprocess.run([str(harp), "version"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "harp" in (result.stdout + result.stderr).lower()


def test_harp_create_help_imports_cleanly():
    """The documented `harp create` command imports without the typing shadow."""
    harp = _console_script("harp")
    if harp is None:
        pytest.skip("harp console script not installed in this environment")
    result = subprocess.run([str(harp), "create", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_python_dash_m_harp_runs_from_repo_root():
    """`python -m harp` from the repo root keeps the repo root (not harp/) on sys.path."""
    env = {**os.environ, "PYTHONPATH": ""}
    result = subprocess.run(
        [sys.executable, "-m", "harp", "version"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "harp" in (result.stdout + result.stderr).lower()
