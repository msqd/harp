import os
import sys

import rich_click as click
from honcho.manager import Manager
from honcho.printer import Printer

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@click.group()
def entrypoint():
    pass


@click.command()
@click.option("--with-docs/--no-docs", default=False)
@click.option("--with-ui/--no-ui", default=False)
def start(with_docs, with_ui):
    processes = {
        "frontend": "(cd frontend; pnpm dev)",
        "proxy": 'watchfiles --filter python "' + sys.executable + ' -m harp.examples.default" harp',
    }
    if with_docs:
        processes["docs"] = "(cd docs; sphinx-autobuild . _build/html)"
    if with_ui:
        processes["ui"] = "(cd vendors/mkui; pnpm serve)"
    manager = Manager(Printer(sys.stdout))
    for name, command in processes.items():
        e = os.environ.copy()
        manager.add_process(name, command, quiet=False, cwd=root_dir, env=e)
    manager.loop()
    sys.exit(manager.returncode)


entrypoint.add_command(start)
