import asyncio

import orjson
from rich.console import Console
from rich.pretty import Pretty
from rich.syntax import Syntax
from rich.tree import Tree

from harp.commandline.options.server import CommonServerOptions, add_harp_server_click_options
from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.utils.commandline import click


@click.command("config", short_help="Prints the current configuration.")
@add_harp_server_click_options
@click.option("--raw", is_flag=True, help="Prints the raw configuration as a dictionary.")
@click.option("--json", is_flag=True, help="Prints the raw configuration as JSON.")
@click.option(
    "--unsecure",
    is_flag=True,
    help="Prints the configuration without hiding sensitive information.",
)
def config(raw=False, json=False, unsecure=False, **kwargs):
    """Compiles and dumps the current configuration, the same way that "server" commands would do it.

    Example:

        $ harp config --file ... --example ... --set ... --endpoint ...

    """
    if raw and json:
        raise click.UsageError("Cannot use both --raw and --json.")

    system = asyncio.run(
        ConfigurationBuilder.from_commandline_options(
            CommonServerOptions(**kwargs),
        ).abuild_system()
    )

    console = Console()
    if raw:
        console.print(Pretty(asdict(system.config)))
    elif json:
        console.print(
            Syntax(
                orjson.dumps(
                    asdict(
                        system.config,
                        secure=not unsecure,
                    ),
                    option=orjson.OPT_INDENT_2,
                ).decode(),
                "json",
                background_color="default",
            )
        )
    else:
        for k, v in system.config.items():
            tree = Tree(f"📦 [bright_white][bold]{k}[/bright_white][/bold]")
            # todo secure/unsecure with pretty print ?
            tree.add(Pretty(v))
            console.print(tree)
