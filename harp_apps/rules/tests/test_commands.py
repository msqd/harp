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
