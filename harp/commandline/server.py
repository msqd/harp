from typing import List, cast

from click import BaseCommand

from harp import run
from harp.commandline.options.server import CommonServerOptions, add_harp_server_click_options
from harp.config import ConfigurationBuilder
from harp.settings import USE_PROMETHEUS
from harp.utils.commandline import click


class FixArgvOptionSetValues(click.Command):
    """
    This class override parse_args click function
    parse args enter in cli when type command
    with space or = for  --set command:

    eg: --set arg=value or arg value
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        index: int = 0
        while index < len(args):
            if args[index] == "--set":
                if index + 2 < len(args):
                    if not (args[index + 1].startswith("-") or args[index + 2].startswith("-")):
                        args[index + 1] += "=" + args[index + 2]
                        del args[index + 2]

            index += 1
        return super().parse_args(ctx, args)


@click.command(
    cls=FixArgvOptionSetValues,
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
