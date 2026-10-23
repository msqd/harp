"""The development environment restarts the server on every change: a password generated at each boot is no use there."""

from harp.commandline.utils.manager import HARP_SERVER_SERVICE, HonchoManagerFactory


def server_command(*proxy_options):
    factory = HonchoManagerFactory(proxy_options=list(proxy_options))
    _cwd, command = factory.commands[HARP_SERVER_SERVICE](factory, {HARP_SERVER_SERVICE})
    return command


def test_dev_server_explicitly_opts_out_of_dashboard_auth():
    assert "--set dashboard.auth.type=none" in server_command()


def test_dev_server_respects_configured_dashboard_auth():
    command = server_command("--set dashboard.auth.type=basic")

    assert "dashboard.auth.type=none" not in command
