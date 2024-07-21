from typing import cast

from click import BaseCommand

from harp import get_logger
from harp.utils.commandline import click

from .lint import lint_command
from .run import run_command

logger = get_logger(__name__)


@click.group("rules")
def entrypoint():
    """Rules engine related commands."""
    pass


entrypoint.add_command(cast(BaseCommand, lint_command))
entrypoint.add_command(cast(BaseCommand, run_command))
