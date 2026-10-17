"""CLI imports and help must not rely on deprecated Click APIs."""

import os
import subprocess
import sys


def test_help_has_no_click_deprecation_warnings():
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-W",
            "error::PendingDeprecationWarning",
            "-m",
            "harp",
            "--help",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )

    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
