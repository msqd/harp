"""Tests for the `harp create` command (subprocess invocation, uv fallback, CLI-driven context)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from harp.commandline.create import create

WHICH_BOTH = {"cookiecutter": "/usr/bin/cookiecutter", "uv": "/usr/bin/uv"}
GIT_AUTHOR = {"user.name": "Ada Lovelace", "user.email": "ada@example.com"}


def _run(args, *, which=None, git=None, cli_input=None):
    """Invoke `create` with `shutil.which`/`get_git_config` stubbed.

    Captures the argv passed to cookiecutter and the JSON context written to the
    `--config-file`, reading the file *during* the (mocked) subprocess call so it is
    still on disk.
    """
    which = WHICH_BOTH if which is None else which
    git = git or {}
    captured = {}

    def _capture(cmd, **kwargs):
        captured["cmd"] = cmd
        if "--config-file" in cmd:
            config_path = cmd[cmd.index("--config-file") + 1]
            captured["config"] = json.loads(Path(config_path).read_text())
        return MagicMock(returncode=0)

    with (
        patch("harp.commandline.create.shutil.which", side_effect=lambda name: which.get(name)),
        patch("harp.commandline.create.get_git_config", side_effect=lambda key: git.get(key)),
        patch("harp.commandline.create.render_example_config", return_value="EXAMPLE-CONFIG") as render,
        patch("harp.commandline.create.subprocess.run", side_effect=_capture) as run,
    ):
        result = CliRunner().invoke(create, ["project", *args], input=cli_input)
    captured["render"] = render
    return result, run, captured


class TestCreateCookiecutterInvocation:
    def test_runs_cookiecutter_binary_when_available(self):
        result, run, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert result.exit_code == 0, result.output
        run.assert_called_once()
        cmd = captured["cmd"]
        assert cmd[0] == "cookiecutter"
        assert "--no-input" in cmd
        assert cmd[-1].endswith("project")

    def test_falls_back_to_uv_tool_run_when_cookiecutter_absent(self):
        result, run, captured = _run(["my-proj"], which={"cookiecutter": None, "uv": "/usr/bin/uv"}, git=GIT_AUTHOR)
        assert result.exit_code == 0, result.output
        cmd = captured["cmd"]
        assert cmd[:4] == ["uv", "tool", "run", "cookiecutter"]
        assert cmd[-1].endswith("project")

    def test_errors_with_uv_message_when_nothing_available(self):
        result, run, _ = _run(["my-proj"], which={"cookiecutter": None, "uv": None}, git=GIT_AUTHOR)
        assert result.exit_code != 0
        run.assert_not_called()
        assert "uv" in result.output.lower()
        assert "poetry" not in result.output.lower()


class TestCreateProjectContext:
    def test_name_argument_is_passed_as_context(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["name"] == "my-proj"

    def test_defaults_enable_application_and_config(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        context = captured["config"]["default_context"]
        assert context["create_application"] is True
        assert context["create_config"] is True

    def test_no_app_flag_disables_application(self):
        _, _, captured = _run(["my-proj", "--no-app"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["create_application"] is False

    def test_no_config_flag_disables_config(self):
        _, _, captured = _run(["my-proj", "--no-config"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["create_config"] is False

    def test_author_is_read_from_git_config(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        context = captured["config"]["default_context"]
        assert context["author_name"] == "Ada Lovelace"
        assert context["author_email"] == "ada@example.com"

    def test_always_runs_non_interactively(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert "--no-input" in captured["cmd"]

    def test_prompts_for_name_when_missing(self):
        _, _, captured = _run([], git=GIT_AUTHOR, cli_input="Prompted Name\n")
        assert captured["config"]["default_context"]["name"] == "Prompted Name"

    def test_prompts_for_author_when_git_config_absent(self):
        _, _, captured = _run(["my-proj"], git={}, cli_input="Jane Doe\njane@doe.net\n")
        context = captured["config"]["default_context"]
        assert context["author_name"] == "Jane Doe"
        assert context["author_email"] == "jane@doe.net"


class TestCreateExampleConfig:
    def test_example_config_is_passed_in_context(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__example_config"] == "EXAMPLE-CONFIG"

    def test_no_config_flag_yields_empty_example_config_without_introspection(self):
        _, _, captured = _run(["my-proj", "--no-config"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__example_config"] == ""
        captured["render"].assert_not_called()


class TestDocsProcessCommand:
    def test_docs_executable_uses_uv_not_poetry(self):
        from harp.commandline.utils.manager import HonchoManagerFactory

        _cwd, command = HonchoManagerFactory()._get_docs_executable(None)
        assert "uv run" in command
        assert "poetry" not in command.lower()
