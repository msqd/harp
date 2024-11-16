from typing import cast

from click import BaseCommand

from harp.utils.commandline import click


@click.command("version", short_help="Shows harp version.")
def version(**kwargs):
    from harp import __hardcoded_version__, __version__

    print(f"HARP version {__version__} ({__hardcoded_version__})")


version = cast(BaseCommand, version)
