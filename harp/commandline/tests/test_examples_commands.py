from harp.commandline.examples import list_command
from harp.utils.testing.cli import CliRunner


def test_list_examples_command(snapshot):
    runner = CliRunner()

    result = runner.invoke(list_command, [])
    assert result.exit_code == 0
    assert result.output.strip() == snapshot

    result = runner.invoke(list_command, ["--raw"])
    assert result.exit_code == 0
    assert result.output.strip() == snapshot
