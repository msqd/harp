"""CLI imports and help must not rely on deprecated Click APIs."""

import os
import subprocess
import sys

# Only Click and rich-click deprecations are ours to fix; other libraries may warn on their own schedule.
RUN_HELP_FAILING_ON_CLICK_DEPRECATIONS = """
import runpy
import sys
import warnings

for category in (DeprecationWarning, PendingDeprecationWarning):
    warnings.filterwarnings("error", category=category, module=r"(rich_)?click(\\.|$)")
    warnings.filterwarnings("error", category=category, message=r".*(?i:click)")

sys.argv = ["harp", "--help"]
runpy.run_module("harp", run_name="__main__")
"""


def test_help_has_no_click_deprecation_warnings():
    result = subprocess.run(
        [sys.executable, "-c", RUN_HELP_FAILING_ON_CLICK_DEPRECATIONS],
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
