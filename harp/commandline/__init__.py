"""
The Command Line (:mod:`harp.commandline`) package bundles everything related to the `harp` command.

It contains an :func:`entrypoint` callable, built using `click`, which is called when you type `harp` in your terminal.

It is a high-level development helper: for example, `harp start` wraps `honcho`, a python process manager (foreman
clone) that can spawn multiple processes to help you with development.

Production environment will favour the lower-level `bin/entrypoint` script, that skips the process manager entirely
and runs the application server directly.

This may be subject to changes in the future (espacially to align/refactor arg parsers), but this approach works
well for now.

.. todo::

    @click.option('--prod/--dev', default=False, help="Set defaults for production or development environment (default
    to dev).")

    @click.option('--verbose', '-v', count=True)
    --verbose : change default log verbosity

    @click.option('--debug', is_flag=True)
    --debug : ?

    Manage process list / options using a class (with hierarchy for prod/dev, for example)
    If one process only, no honcho ? Or mayne no honcho manager ?

Contents
--------

.. click:: harp.commandline:entrypoint
   :prog: harp
   :nested: full

"""

import rich_click as click

from harp.commandline.install_dev import install_dev
from harp.commandline.start import start

__title__ = "Command Line"


@click.group()
def entrypoint():
    """HTTP Application Runtime Proxy (HARP)

    The following commands are available to help you setup and run your HTTP proxy application.

    """
    pass


entrypoint.add_command(start)
entrypoint.add_command(install_dev)

__all__ = [
    "entrypoint",
    "start",
    "install_dev",
]
