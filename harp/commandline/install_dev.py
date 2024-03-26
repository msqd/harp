import os
import subprocess

import rich_click as click

from harp import ROOT_DIR


@click.command(short_help="Installs the development dependencies.")
def install_dev():
    click.secho("Installing dashboards development dependencies...", bold=True)
    subprocess.run(["pnpm", "install"], cwd=os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend"))
