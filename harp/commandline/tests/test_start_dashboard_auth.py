"""The development environment restarts the server on every change: a password generated at each boot is no use there."""

import pytest

from harp.commandline.options.server import CommonServerOptions
from harp.commandline.utils.manager import development_server_options
from harp.config import ConfigurationBuilder

BASIC_AUTH = """
dashboard:
  auth:
    type: basic
    algorithm: plaintext
    users:
      alice: secret
"""


def build_settings(options: list[str], files: tuple = ()):
    """Builds the settings the way the server command does, from the options `start` hands to it."""
    option_pairs = [o.split(" ", 1)[1].split("=", 1) for o in options if o.startswith("--set ")]
    return ConfigurationBuilder.from_commandline_options(CommonServerOptions(files=files, options=option_pairs)).build()


@pytest.fixture
def basic_file(tmp_path):
    path = tmp_path / "basic.yml"
    path.write_text(BASIC_AUTH)
    return str(path)


def test_dev_server_explicitly_opts_out_of_dashboard_auth():
    options = development_server_options(CommonServerOptions())

    assert "--set dashboard.auth.type=none" in options
    assert build_settings(options)["dashboard"].auth.type == "none"


def test_dev_server_keeps_basic_auth_configured_in_a_file(basic_file):
    server_options = CommonServerOptions(files=(basic_file,))

    options = development_server_options(server_options)

    assert "--set dashboard.auth.type=none" not in options
    assert build_settings(options, files=(basic_file,))["dashboard"].auth.type == "basic"


def test_dev_server_respects_dashboard_auth_set_on_the_command_line():
    options = development_server_options(CommonServerOptions(options=[("dashboard.auth.type", "none")]))

    assert options.count("--set dashboard.auth.type=none") == 1
