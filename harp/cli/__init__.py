import os
import sys

import rich_click as click

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@click.group()
def entrypoint():
    pass


@click.command(short_help="Starts the development environment.")
@click.option("--with-docs/--no-docs", default=False)
@click.option("--with-ui/--no-ui", default=False)
@click.option("--set", "options", default=(), multiple=True, help="Set proxy configuration options.")
@click.argument("services", nargs=-1)
def start(with_docs, with_ui, options, services):
    try:
        from honcho.manager import Manager
        from honcho.printer import Printer
    except ImportError as exc:
        raise click.UsageError(
            "You must install development dependencies to start the development environment"
        ) from exc

    options = (
        "--set {key} {value}".format(key=key, value=value) for key, value in map(lambda x: x.split("=", 1), options)
    )
    processes = {
        "frontend": "(cd frontend; pnpm dev)",
        "proxy": 'watchfiles --filter python "'
        + sys.executable
        + " -m harp.examples.default"
        + (f" {' '.join(options)}" if options else "")
        + '" harp',
    }
    if with_docs or "docs" in services:
        processes["docs"] = "(cd docs; sphinx-autobuild . _build/html)"
    if with_ui or "ui" in services:
        processes["ui"] = "(cd vendors/mkui; pnpm serve)"

    # allow to limit the services to start
    if services:
        unknown_services = set(services) - set(processes.keys())
        if unknown_services:
            raise click.UsageError(f"Unknown services: {', '.join(unknown_services)}")
        processes = {k: v for k, v in processes.items() if k in services}

    manager = Manager(Printer(sys.stdout))
    for name, command in processes.items():
        e = os.environ.copy()
        manager.add_process(name, command, quiet=False, cwd=root_dir, env=e)
    manager.loop()
    sys.exit(manager.returncode)


entrypoint.add_command(start)
