"""Tests for the `harp create` command's cookiecutter invocation (subprocess, uv fallback)."""

from unittest.mock import patch

from click.testing import CliRunner

from harp.commandline.create import create


def _invoke(which_map):
    """Invoke `create project` with shutil.which stubbed from which_map, capturing subprocess.run."""
    with (
        patch("harp.commandline.create.shutil.which", side_effect=lambda name: which_map.get(name)),
        patch("harp.commandline.create.subprocess.run") as run,
    ):
        result = CliRunner().invoke(create, ["project"])
    return result, run


class TestCreateCookiecutterInvocation:
    def test_runs_cookiecutter_binary_when_available(self):
        result, run = _invoke({"cookiecutter": "/usr/bin/cookiecutter", "uv": "/usr/bin/uv"})
        assert result.exit_code == 0, result.output
        run.assert_called_once()
        args = run.call_args.args[0]
        assert args[0] == "cookiecutter"
        assert args[-1].endswith("project")

    def test_falls_back_to_uv_tool_run_when_cookiecutter_absent(self):
        result, run = _invoke({"cookiecutter": None, "uv": "/usr/bin/uv"})
        assert result.exit_code == 0, result.output
        run.assert_called_once()
        args = run.call_args.args[0]
        assert args[:4] == ["uv", "tool", "run", "cookiecutter"]
        assert args[-1].endswith("project")

    def test_errors_with_uv_message_when_nothing_available(self):
        result, run = _invoke({"cookiecutter": None, "uv": None})
        assert result.exit_code != 0
        run.assert_not_called()
        assert "uv" in result.output.lower()
        assert "poetry" not in result.output.lower()


class TestDocsProcessCommand:
    def test_docs_executable_uses_uv_not_poetry(self):
        from harp.commandline.utils.manager import HonchoManagerFactory

        _cwd, command = HonchoManagerFactory()._get_docs_executable(None)
        assert "uv run" in command
        assert "poetry" not in command.lower()
