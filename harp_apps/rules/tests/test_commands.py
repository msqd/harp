import pytest

from harp.commandline import entrypoint
from harp.utils.testing.cli import CliRunner


def test_run_command(httpbin, snapshot):
    runner = CliRunner()

    result = runner.invoke(entrypoint, ["rules", "run", "api=" + httpbin, "GET", "/hostname"])
    assert result.exit_code == 0
    assert result.stdout.strip() == snapshot


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
    assert "No such option: --set" in result.output
    assert not isinstance(result.exception, TypeError)
