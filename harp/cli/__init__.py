"""

To do
-----

@click.option('--prod/--dev', default=False, help="Set defaults for production or development environment (default to dev).")

@click.option('--verbose', '-v', count=True)
--verbose : change default log verbosity

@click.option('--debug', is_flag=True)
--debug : ?

Manage process list / options using a class (with hierarchy for prod/dev, for example)
If one process only, no honcho ? Or mayne no honcho manager ?

"""

import rich_click as click

from harp.cli.install_dev import install_dev
from harp.cli.start import start


@click.group()
def entrypoint():
    pass


entrypoint.add_command(start)
entrypoint.add_command(install_dev)
