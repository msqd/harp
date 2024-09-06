import importlib.util
import sys

from harp.commandline.server import CommonServerOptions, add_harp_server_click_options
from harp.commandline.utils.manager import HARP_DASHBOARD_SERVICE
from harp.utils.commandline import click, code


def _get_service_name_for_humans(x: str):
    if ":" in x:
        return x.split(":", 1)[1]
    return x


def assert_package_is_available(package_name: str):
    if importlib.util.find_spec(package_name) is None:
        raise ModuleNotFoundError(f"Package {package_name!r} is not available.")


def assert_development_packages_are_available():
    assert_package_is_available("honcho")
    assert_package_is_available("watchfiles")


@click.command(
    short_help="Starts the local development environment.",
    help=f"""Starts the local development environment, using honcho to spawn a configurable set of processes that you
    can adapt to your needs. By default, it will starts the `dashboard` (frontend dev server) and `server` (python
    server) processes. For live instances, you'll prefer {code("harp server")}.""",
)
@click.option(
    "--with-docs/--no-docs",
    default=False,
    help="Append the sphinx doc process to the process list.",
)
@click.option(
    "--with-ui/--no-ui",
    default=False,
    help="Append the storybook process to the process list.",
)
@click.option(
    "--mock",
    is_flag=True,
    help="Enable mock data instead of real api data (dashboard only).",
)
@click.option(
    "--server-subprocess",
    "-XS",
    "server_subprocesses",
    metavar="NAME:PORT:CMD",
    multiple=True,
    help="Add a server subprocess to the list of services to start (experimental, can be used multiple times).",
)
@add_harp_server_click_options
@click.argument("services", nargs=-1)
def start(with_docs, with_ui, services, server_subprocesses, mock, **kwargs):
    try:
        assert_development_packages_are_available()
    except ModuleNotFoundError as exc:
        raise click.UsageError(
            "\n".join(
                (
                    "You must install development dependencies to start the development environment.",
                    "",
                    'Try to install the "dev" extra.',
                )
            )
        ) from exc

    from harp.commandline.utils.manager import (
        HARP_DOCS_SERVICE,
        HARP_UI_SERVICE,
        HonchoManagerFactory,
        parse_server_subprocesses_options,
    )

    more_env = {}

    if not mock:
        more_env.setdefault(HARP_DASHBOARD_SERVICE, {})["DISABLE_MOCKS"] = "true"

    options = CommonServerOptions(**kwargs)
    _dashboard_devserver_port = options.options.get("dashboard.devserver.port", None)

    manager_factory = HonchoManagerFactory(
        proxy_options=options.as_list(),
        dashboard_devserver_port=_dashboard_devserver_port,
    )

    services = {f"harp:{_name}" for _name in services or ()} or set(manager_factory.defaults)
    if with_docs or HARP_DOCS_SERVICE in services:
        services.add(HARP_DOCS_SERVICE)
    if with_ui or HARP_UI_SERVICE in services:
        services.add(HARP_UI_SERVICE)

    for _name, (_proxy_port, _path, _cmd, _port) in parse_server_subprocesses_options(server_subprocesses).items():
        if _name in services or _name in manager_factory.names:
            raise click.UsageError(f"Duplicate process name: {_name}.")
        services.add(_name)
        manager_factory.names.add(_name)
        manager_factory.proxy_ports[_name] = _proxy_port
        manager_factory.ports[_name] = _port
        manager_factory.commands[_name] = _cmd
        manager_factory.cwds[_name] = _path

    # allow to limit the services to start
    if services:
        unknown_services = set(services) - manager_factory.names
        if unknown_services:
            unknown_services_as_string = ", ".join(map(_get_service_name_for_humans, sorted(unknown_services)))
            known_services_as_string = ", ".join(map(_get_service_name_for_humans, sorted(manager_factory.names)))
            raise click.UsageError(
                f"Unknown services: {unknown_services_as_string}. Available: {known_services_as_string}."
            )

    manager = manager_factory.build(services, more_env=more_env)

    try:
        manager.loop()
    finally:
        manager.terminate()
        manager.kill()

    sys.exit(manager.returncode)
