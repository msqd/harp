from typing import cast

from click import BaseCommand

from harp import run
from harp.commandline.options.server import CommonServerOptions, server_command
from harp.config.utils import get_configuration_builder_type


@server_command(
    short_help="Starts HARP server.",
    help="""Starts HARP server, using the provided configuration. This is the main process and will be the only process
    you need on a live server, it will serve both the proxy ports and the compiled frontend assets (dashboard).""",
)
def server(**kwargs):
    from prometheus_client import Enum

    _info = Enum(
        "harp",
        "HARP status information.",
        states=["setup", "up", "teardown", "down"],
    )
    _info.state("setup")

    configration_builder = get_configuration_builder_type()

    builder = configration_builder.from_commandline_options(CommonServerOptions(**kwargs))

    _info.state("up")

    try:
        return run(builder)
    finally:
        _info.state("down")


server = cast(BaseCommand, server)
