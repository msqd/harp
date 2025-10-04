"""
Testing utilities for Click CLI applications.
"""

from click.testing import CliRunner as BaseCliRunner


class CliRunner(BaseCliRunner):
    """
    Custom CliRunner that forces terminal width to 80 columns for consistent output.

    This ensures that CLI output in tests is consistent regardless of the actual terminal
    size, which is important for snapshot testing and reproducible test results.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("env", {})
        kwargs["env"]["COLUMNS"] = "80"
        super().__init__(*args, **kwargs)
