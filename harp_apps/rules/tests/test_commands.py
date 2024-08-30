from click.testing import CliRunner

from harp.commandline import entrypoint


def test_run_command(httpbin, snapshot):
    runner = CliRunner()

    result = runner.invoke(entrypoint, ["rules", "run", "api=" + httpbin, "GET", "/hostname"])
    assert result.exit_code == 0
    assert result.output.strip() == snapshot


def test_lint_command(snapshot):
    runner = CliRunner()

    result = runner.invoke(entrypoint, ["rules", "lint"])
    assert result.exit_code == 0
    assert result.output.strip() == snapshot
