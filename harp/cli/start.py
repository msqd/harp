import importlib.util
import sys
from itertools import chain

import rich_click as click

from harp.cli.utils.manager import (
    HARP_DOCS_SERVICE,
    HARP_UI_SERVICE,
    HonchoManagerFactory,
    parse_server_subprocesses_options,
)


def _get_service_name_for_humans(x: str):
    if ":" in x:
        return x.split(":", 1)[1]
    return x


@click.command(short_help="Starts the development environment.")
@click.option("--set", "options", default=(), multiple=True, help="Set proxy configuration options.")
@click.option("--file", "-f", "files", default=(), multiple=True, help="Load configuration from file.")
@click.option("--with-docs/--no-docs", default=False)
@click.option("--with-ui/--no-ui", default=False)
@click.option(
    "--server-subprocess",
    "-XS",
    "server_subprocesses",
    multiple=True,
    help="Add a server subprocess to the list of services to start.",
)
@click.argument("services", nargs=-1)
def start(with_docs, with_ui, options, files, services, server_subprocesses):
    try:
        importlib.util.find_spec("honcho")
        importlib.util.find_spec("watchfiles")
    except ImportError as exc:
        # todo when released on pypi, add more help
        raise click.UsageError(
            "\n".join(
                (
                    "You must install development dependencies to start the development environment.",
                    "",
                    'Try to install the "dev" extra.',
                )
            )
        ) from exc

    manager_factory = HonchoManagerFactory(
        proxy_options=list(
            chain(
                (
                    "--set {key} {value}".format(key=key, value=value)
                    for key, value in map(lambda x: x.split("=", 1), options)
                ),
                ("-f " + file for file in files),
            )
        )
    )

    services = {f"harp:{_name}" for _name in services or ()} or set(manager_factory.defaults)
    if with_docs or HARP_DOCS_SERVICE in services:
        services.add(HARP_DOCS_SERVICE)
    if with_ui or HARP_UI_SERVICE in services:
        services.add(HARP_UI_SERVICE)

    for _name, (_proxy_port, _cmd, _port) in parse_server_subprocesses_options(server_subprocesses).items():
        if _name in services:
            raise click.UsageError(f"Duplicate process name: {_name}.")
        services.add(_name)
        manager_factory.proxy_ports[_name] = _proxy_port
        manager_factory.ports[_name] = _port
        manager_factory.commands[_name] = _cmd

    # allow to limit the services to start
    if services:
        unknown_services = set(services) - manager_factory.names
        if unknown_services:
            unknown_services_as_string = ", ".join(map(_get_service_name_for_humans, sorted(unknown_services)))
            known_services_as_string = ", ".join(map(_get_service_name_for_humans, sorted(manager_factory.names)))
            raise click.UsageError(
                f"Unknown services: {unknown_services_as_string}. Available: {known_services_as_string}."
            )

    manager = manager_factory.build(services)
    manager.loop()
    sys.exit(manager.returncode)
