from typing import cast

from click import BaseCommand

from harp import run
from harp.commandline.options.server import CommonServerOptions, add_harp_server_click_options
from harp.config import ConfigurationBuilder
from harp.settings import USE_PROMETHEUS
from harp.utils.commandline import click


@click.command(
    short_help="Starts HARP server.",
    help="""Starts HARP server, using the provided configuration. This is the main process and will be the only process
    you need on a live server, it will serve both the proxy ports and the compiled frontend assets (dashboard).""",
)
@add_harp_server_click_options
def server(**kwargs):
    _info = None
    if USE_PROMETHEUS:
        from prometheus_client import Enum

        _info = Enum(
            "harp",
            "HARP status information.",
            states=["setup", "up", "teardown", "down"],
        )
        _info.state("setup")

    builder = ConfigurationBuilder.from_commandline_options(CommonServerOptions(**kwargs))

    if _info:
        _info.state("up")

    try:
        return run(builder)
    finally:
        if _info:
            _info.state("down")


server = cast(BaseCommand, server)
