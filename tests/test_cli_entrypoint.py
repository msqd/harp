"""Regression tests for running the HARP CLI from a source checkout.

Guards against the class of failure where the ``harp/`` package directory ends
up on ``sys.path`` and a first-party submodule shadows a stdlib module (the
former ``harp/typing`` shadowed stdlib ``typing``). This surfaced because ``harp``
had no console entry point, so ``uv run harp ...`` executed the package
*directory* instead of a script.

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


@pytest.mark.xfail(
    reason="harp/http still shadows the stdlib `http` module under directory execution; "
    "renaming it is a larger BC break on core public API, pending decision (#827 discussion).",
    strict=False,
)
def test_running_package_directory_does_not_shadow_stdlib():
    """Executing the package directory puts harp/ on sys.path[0]; no submodule may shadow the stdlib.

    This is the invocation that still crashed after the console-script fix (#826): a first-party
    module sharing a stdlib name (the former ``harp/typing``) shadowed the real ``typing``.
    Renaming ``harp/typing`` removes that clash; ``harp/http`` remains (tracked separately).
    """
    env = {**os.environ, "PYTHONPATH": ""}
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "harp" / "__main__.py"), "version"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "harp" in (result.stdout + result.stderr).lower()


def test_no_new_first_party_module_shadows_a_stdlib_top_level_module():
    """No top-level ``harp/`` submodule may share a name with a stdlib top-level module.

    ``http`` is a known, pre-existing clash (core public API — renaming is a larger BC break,
    tracked separately); it is allow-listed so this guard still catches *new* regressions.
    """
    known_clashes = {"http"}
    harp_dir = REPO_ROOT / "harp"
    submodules = {
        entry.name[:-3] if entry.name.endswith(".py") else entry.name
        for entry in harp_dir.iterdir()
        if (entry.is_dir() and (entry / "__init__.py").exists())
        or (entry.suffix == ".py" and entry.name not in {"__init__.py", "__main__.py"})
    }
    clashes = (submodules & sys.stdlib_module_names) - known_clashes
    assert not clashes, f"first-party modules shadow stdlib top-level modules: {sorted(clashes)}"
