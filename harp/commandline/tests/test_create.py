"""Tests for the `harp create` command (subprocess invocation, uv fallback, CLI-driven context)."""

import json
import subprocess
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

from click import unstyle
from click.testing import CliRunner

from harp.commandline.create import create, harp_requirement, literal

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
        assert cmd[:6] == ["uv", "tool", "run", "--from", "cookiecutter==2.6.0", "cookiecutter"]
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
        assert captured["config"]["default_context"]["name"] == literal("my-proj")

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
        assert context["author_name"] == literal("Ada Lovelace")
        assert context["author_email"] == literal("ada@example.com")

    def test_always_runs_non_interactively(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert "--no-input" in captured["cmd"]

    def test_prompts_for_name_when_missing(self):
        _, _, captured = _run([], git=GIT_AUTHOR, cli_input="Prompted Name\n")
        assert captured["config"]["default_context"]["name"] == literal("Prompted Name")

    def test_prompts_for_author_when_git_config_absent(self):
        _, _, captured = _run(["my-proj"], git={}, cli_input="Jane Doe\njane@doe.net\n")
        context = captured["config"]["default_context"]
        assert context["author_name"] == literal("Jane Doe")
        assert context["author_email"] == literal("jane@doe.net")


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


class TestHarpRequirement:
    """The generated project's harp-proxy floor derives from the installed harp version."""

    def test_stable_release_floors_at_the_release(self):
        assert harp_requirement("0.10.0") == "harp-proxy>=0.10.0"

    def test_post_release_floors_at_the_release(self):
        assert harp_requirement("0.10.0.post1") == "harp-proxy>=0.10.0"

    def test_pre_release_floors_at_dev0_of_the_release(self):
        assert harp_requirement("0.11.0a1") == "harp-proxy>=0.11.0.dev0"
        assert harp_requirement("0.11.0rc2") == "harp-proxy>=0.11.0.dev0"

    def test_dev_build_floors_at_dev0_of_the_release(self):
        assert harp_requirement("0.11.0.dev0") == "harp-proxy>=0.11.0.dev0"
        assert harp_requirement("0.11.0.dev3+g1234abc") == "harp-proxy>=0.11.0.dev0"

    def test_context_carries_the_requirement_of_the_installed_version(self):
        with patch("harp.commandline.create.importlib.metadata.version", return_value="0.11.0.dev0"):
            _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__harp_requirement"] == "harp-proxy>=0.11.0.dev0"


class TestHarpSource:
    """`--harp-source` / `HARP_SOURCE` scaffold the project against a local harp checkout."""

    def test_defaults_to_no_source(self):
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__harp_source"] == literal("")

    def test_option_passes_the_checkout_path(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        _, _, captured = _run(["my-proj", "--harp-source", str(tmp_path)], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__harp_source"] == literal(str(tmp_path))

    def test_environment_variable_is_the_default(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.setenv("HARP_SOURCE", str(tmp_path))
        _, _, captured = _run(["my-proj"], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__harp_source"] == literal(str(tmp_path))

    def test_relative_path_is_made_absolute(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path.parent)
        _, _, captured = _run(["my-proj", "--harp-source", tmp_path.name], git=GIT_AUTHOR)
        assert captured["config"]["default_context"]["__harp_source"] == literal(str(tmp_path))

    def test_rejects_a_directory_that_is_not_a_checkout(self, tmp_path):
        result, run, _ = _run(["my-proj", "--harp-source", str(tmp_path)], git=GIT_AUTHOR)
        assert result.exit_code != 0
        assert "pyproject.toml" in result.output
        run.assert_not_called()

    def test_rejects_a_missing_path(self, tmp_path):
        result, run, _ = _run(["my-proj", "--harp-source", str(tmp_path / "nope")], git=GIT_AUTHOR)
        assert result.exit_code != 0
        run.assert_not_called()

    def test_help_documents_the_option(self):
        result = CliRunner().invoke(create, ["--help"])
        assert "--harp-source" in result.output
        assert "HARP_SOURCE" in result.output


TRICKY = "Eve {{ 7*7 }} {% raw %}{% endraw %} \"Q\" \\ $(touch pwned) 'x' `id`"


class TestLiteral:
    def test_wraps_the_value_so_cookiecutter_does_not_evaluate_it(self):
        assert literal("a {{ b }}") == "{% raw %}a {{ b }}{% endraw %}"

    def test_neutralises_an_embedded_endraw(self):
        from jinja2 import Environment

        rendered = Environment().from_string(literal("x {% endraw %} {{ 1 }} y")).render()
        assert rendered == "x {% endraw %} {{ 1 }} y"


class TestVerbatimUserInput:
    """Author and project name reach the generated project as typed, whatever they contain."""

    def _generate(self, tmp_path, monkeypatch, *, name=TRICKY, author=TRICKY, email="e@x.net"):
        monkeypatch.chdir(tmp_path)
        git = {"user.name": author, "user.email": email}
        with (
            patch("harp.commandline.create.get_git_config", side_effect=lambda key: git.get(key)),
            patch("harp.commandline.create.render_example_config", return_value=""),
        ):
            result = CliRunner().invoke(create, ["project", name])
        assert result.exit_code == 0, result.output
        (project_dir,) = [path for path in tmp_path.iterdir() if path.is_dir()]
        return project_dir

    def test_pyproject_is_valid_toml_with_the_literal_author(self, tmp_path, monkeypatch):
        project_dir = self._generate(tmp_path, monkeypatch)
        pyproject = tomllib.loads((project_dir / "pyproject.toml").read_text())
        assert pyproject["project"]["authors"] == [{"name": TRICKY, "email": "e@x.net"}]

    def test_readme_title_is_the_literal_name(self, tmp_path, monkeypatch):
        project_dir = self._generate(tmp_path, monkeypatch)
        assert (project_dir / "README.rst").read_text().startswith(f"Example: {TRICKY}\n")

    def test_initial_commit_author_is_the_literal_author(self, tmp_path, monkeypatch):
        project_dir = self._generate(tmp_path, monkeypatch)
        log = subprocess.run(
            ["git", "log", "-1", "--format=%an"], cwd=project_dir, capture_output=True, text=True, check=True
        )
        assert log.stdout.strip() == TRICKY

    def test_nothing_is_executed(self, tmp_path, monkeypatch):
        self._generate(tmp_path, monkeypatch)
        assert not list(tmp_path.rglob("pwned"))

    def test_makefile_help_title_is_the_literal_name(self, tmp_path, monkeypatch):
        project_dir = self._generate(tmp_path, monkeypatch, name='Q "x" $HOME')
        result = subprocess.run(["make", "help"], cwd=project_dir, capture_output=True, text=True)
        assert 'Q "x" $HOME' in result.stdout


class TestCreateHelp:
    def test_defines_a_project_and_links_to_the_developer_quick_start(self):
        result = CliRunner().invoke(create, ["--help"], terminal_width=120, env={"NO_COLOR": "1", "FORCE_COLOR": None})

        assert result.exit_code == 0, result.output
        # rich-click colours each wrapped line: compare the plain words.
        help_text = " ".join(unstyle(result.output).split())
        assert "A HARP project is a minimal Python package" in help_text
        assert "your configuration and optional custom application code" in help_text
        assert "https://docs.harp-project.net/en/latest/develop/quick-start.html" in help_text
