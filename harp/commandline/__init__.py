"""

To do
-----

@click.option('--prod/--dev', default=False, help="Set defaults for production or development environment (default to
dev).")

@click.option('--verbose', '-v', count=True)
--verbose : change default log verbosity

@click.option('--debug', is_flag=True)
--debug : ?

Manage process list / options using a class (with hierarchy for prod/dev, for example)
If one process only, no honcho ? Or mayne no honcho manager ?


The `entrypoint` callable is the entrypoint for the `harp` command line interface, installed into your environment when
running either `poetry install`or `pip install`.

It must be considered as a high-level development helper: for example, `harp start` wraps `honcho`, a python
process manager (foreman clone) that can spawn multiple processes to help you with development.

Production environment will favour the lower-level `bin/entrypoint` script, that skips the process manager entirely
and runs the application server directly.

This may be subject to changes in the future (espacially to align/refactor arg parsers), but this approach works
well for now.

"""

import rich_click as click

from harp.commandline.install_dev import install_dev
from harp.commandline.start import start


@click.group()
def entrypoint():
    """HTTP Application Runtime Proxy (HARP)

    The following commands are available to help you setup and run your HTTP proxy application.

    """
    pass


entrypoint.add_command(start)
entrypoint.add_command(install_dev)
