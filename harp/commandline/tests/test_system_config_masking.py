"""``harp-proxy system config`` masks secrets unless asked not to.

The command carries an ``--unsecure`` flag, which tells a reader that the default is safe. It has
to be, because the natural thing to do with this command's output is paste it into a bug report.
"""

import pytest

from harp.commandline.system import config_subcommand
from harp.utils.testing.cli import CliRunner

DSN = "redis://harp:sup3rs3cr3t@cache.internal:6379/0"


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "harp.yml"
    path.write_text(
        "applications: [storage]\n"
        "storage:\n"
        f"  url: sqlite+aiosqlite:///{tmp_path / 'harp.db'}\n"
        "  redis:\n"
        f"    url: {DSN}\n"
    )
    return str(path)


@pytest.mark.parametrize("options", [[], ["--raw"], ["--json"]])
def test_the_password_is_masked_by_default(config_file, options):
    result = CliRunner().invoke(config_subcommand, [*options, "--file", config_file])

    assert result.exit_code == 0, result.output
    assert "sup3rs3cr3t" not in result.output
    assert "cache.internal" in result.output


@pytest.mark.parametrize("options", [[], ["--raw"], ["--json"]])
def test_unsecure_shows_the_password(config_file, options):
    result = CliRunner().invoke(config_subcommand, [*options, "--unsecure", "--file", config_file])

    assert result.exit_code == 0, result.output
    assert "sup3rs3cr3t" in result.output
