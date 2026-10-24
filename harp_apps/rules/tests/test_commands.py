import re

import click
import pytest

from harp.commandline import entrypoint
from harp.utils.testing.cli import CliRunner


def test_run_command(httpbin, snapshot):
    runner = CliRunner()

    result = runner.invoke(entrypoint, ["rules", "run", "api=" + httpbin, "GET", "/hostname"])
    assert result.exit_code == 0
    # Remote dumps carry the ephemeral port and the current date.
    stable = re.sub(r"^(host|date|user-agent): .*$", r"\1: <\1>", result.stdout.strip(), flags=re.MULTILINE)
    assert stable == snapshot


@pytest.mark.parametrize("env", [{"FORCE_COLOR": "3"}, {"NO_COLOR": "1"}])
def test_run_command_ignores_color_environment(httpbin, monkeypatch, env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    result = CliRunner().invoke(entrypoint, ["rules", "run", "api=" + httpbin, "GET", "/hostname"])
    assert result.exit_code == 0
    assert "\x1b" not in result.stdout


def test_lint_command(snapshot):
    runner = CliRunner()

    result = runner.invoke(entrypoint, ["rules", "lint"])
    assert result.exit_code == 0
    assert result.output.strip() == snapshot


def test_run_command_ends_the_transaction(httpbin, monkeypatch):
    from harp_apps.proxy.controllers import HttpProxyController

    ended = []
    end_transaction = HttpProxyController.end_transaction

    async def spy(self, transaction, response):
        ended.append(transaction.id)
        return await end_transaction(self, transaction, response)

    monkeypatch.setattr(HttpProxyController, "end_transaction", spy)

    result = CliRunner().invoke(entrypoint, ["rules", "run", "api=" + httpbin, "GET", "/hostname"])
    assert result.exit_code == 0
    assert len(ended) == 1


@pytest.mark.parametrize("command", ["lint", "run"])
def test_rules_help_only_advertises_supported_configuration_options(command):
    result = CliRunner().invoke(entrypoint, ["rules", command, "--help"])

    assert result.exit_code == 0, result.output
    assert "--file" in result.output
    assert "--example" in result.output
    assert "--set" not in result.output


def test_unsupported_rules_options_have_a_usage_error():
    from click import UsageError

    from harp_apps.rules.commandline.utils.loaders import load_ruleset_from_files

    with pytest.raises(UsageError, match="Unsupported options: foo=bar, baz=qux"):
        load_ruleset_from_files((), (), (("foo", "bar"), ("baz", "qux")))


@pytest.mark.parametrize("command", ["lint", "run"])
@pytest.mark.parametrize("options", [["--set", "foo=bar"], ["--set", "foo", "bar"]])
def test_rules_reject_set_as_an_unknown_option(command, options):
    result = CliRunner().invoke(entrypoint, ["rules", command, *options])

    assert result.exit_code == 2
    # rich-click colours and wraps its error panel: compare the plain words.
    assert "No such option: --set" in " ".join(click.unstyle(result.output).split())
    assert not isinstance(result.exception, TypeError)


def test_run_command_fires_on_remote_request_rules(httpbin, tmp_path):
    rules = tmp_path / "rules.toml"
    rules.write_text('[rules."*"."GET *"]\non_remote_request = """\nrequest.headers["x-rule-fired"] = "yes"\n"""\n')

    result = CliRunner().invoke(entrypoint, ["rules", "run", "--file", str(rules), "api=" + httpbin, "GET", "/headers"])

    assert result.exit_code == 0, result.output
    assert "X-Rule-Fired" in result.stdout
