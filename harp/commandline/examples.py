from typing import cast

from click import Command
from rich.tree import Tree

from harp import get_logger
from harp.config.examples import get_available_examples
from harp.utils.commandline import click
from harp.utils.console import console

logger = get_logger(__name__)


@click.group("examples")
def entrypoint():
    """Examples related commands."""
    pass


@click.command("list")
@click.option("--raw", is_flag=True, help="Simple output without any decoration.")
def list_command(raw=False):
    """List available examples."""

    if raw:
        for example in get_available_examples():
            click.echo(example)
    else:
        tree = Tree("List of available examples")
        for example in get_available_examples():
            tree.add(example)
        console.print(tree)


list_command = cast(Command, list_command)

entrypoint.add_command(list_command)


entrypoint = cast(Command, entrypoint)
