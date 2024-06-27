import os
import subprocess
from typing import cast

from click import BaseCommand

from harp import ROOT_DIR
from harp.utils.commandline import click


@click.command(short_help="Installs the development dependencies.")
def install_dev():
    click.secho("Installing dashboards development dependencies...", bold=True)
    subprocess.run(["pnpm", "install"], cwd=os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend"))


install_dev = cast(BaseCommand, install_dev)
