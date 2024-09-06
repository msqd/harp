"""
The Command Line (:mod:`harp.commandline`) package bundles everything related to the `harp` command.

It contains an :func:`entrypoint` callable, built using `click`, which is called when you type `harp` in your terminal.

It is a high-level development helper: for example, `harp start` wraps `honcho`, a python process manager (foreman
clone) that can spawn multiple processes to help you with development.

Production environment will favour the lower-level `bin/entrypoint` script, that skips the process manager entirely
and runs the application server directly.

This may be subject to changes in the future (especially to align/refactor arg parsers), but this approach works
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

.. todo::

    Possible future things (or not)

    - build (compile stuff for production)
    - serve (run a production-like server)

    Document how harp start work (honcho, devserver port, ...)

"""

from typing import cast

from click import Command

from harp.commandline.config import config
from harp.commandline.examples import entrypoint as examples
from harp.commandline.server import server
from harp.settings import HARP_ENV
from harp.utils.commandline import check_packages, click, code

__title__ = "Command Line"

IS_DEVELOPMENT_ENVIRONMENT = False

if HARP_ENV == "dev" or check_packages("honcho", "watchfiles"):
    IS_DEVELOPMENT_ENVIRONMENT = True

if HARP_ENV == "prod":
    IS_DEVELOPMENT_ENVIRONMENT = False


@click.group()
def entrypoint():
    """HTTP Application Runtime Proxy (HARP)

    The following commands are available to help you setup and run your HTTP proxy application.

    """
    pass


if IS_DEVELOPMENT_ENVIRONMENT:
    from harp.commandline.start import start

    entrypoint.add_command(start)

    from harp.commandline.install import install_dev

    entrypoint.add_command(install_dev)
else:

    @click.command(
        short_help="Starts the local development environment.",
        help=f"""Starts the local development environment, using honcho to spawn a configurable set of processes that you
        can adapt to your needs. By default, it will starts the `dashboard` (frontend dev server) and `server` (python
        server) processes. For live instances, you'll prefer {code("harp server")}.""",
    )
    def start(*args, **kwargs):
        raise NotImplementedError(
            "This command is not available in production environment, please install the dev extra if you need it."
        )

    entrypoint.add_command(start)


if check_packages("alembic"):
    from harp.commandline.migrations import create_migration, feature, history, migrate, reset, run_db_merge_command

    entrypoint.add_command(migrate)
    entrypoint.add_command(feature)
    entrypoint.add_command(history)
    entrypoint.add_command(reset)
    entrypoint.add_command(run_db_merge_command)

    if IS_DEVELOPMENT_ENVIRONMENT:
        entrypoint.add_command(create_migration)

if check_packages("harp_apps.rules.commandline"):
    from harp_apps.rules.commandline import entrypoint as rules_entrypoint

    entrypoint.add_command(cast(Command, rules_entrypoint))

entrypoint.add_command(server)
entrypoint.add_command(config)
entrypoint.add_command(examples)

__all__ = [
    "entrypoint",
]
