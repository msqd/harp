import os
import shlex
import sys
from string import Template

import rich_click as click

from harp import ROOT_DIR, get_logger
from harp.utils.network import get_available_network_port

HARP_DASHBOARD_SERVICE = "harp:dashboard"
HARP_DOCS_SERVICE = "harp:docs"
HARP_SERVER_SERVICE = "harp:server"
HARP_UI_SERVICE = "harp:ui"

logger = get_logger(__name__)


def quote(x):
    return shlex.quote(str(x))


class HonchoManagerFactory:
    defaults = {HARP_DASHBOARD_SERVICE, HARP_SERVER_SERVICE}
    commands = {}

    def __init__(self, *, proxy_options=(), dashboard_devserver_port=None):
        self.ports = {HARP_DASHBOARD_SERVICE: dashboard_devserver_port or get_available_network_port()}
        self.proxy_ports = {}
        self.proxy_options = proxy_options
        self.cwds = {}

        # copy to allow changes on this instance only
        self.names = {
            HARP_DASHBOARD_SERVICE,
            HARP_SERVER_SERVICE,
            HARP_DOCS_SERVICE,
            HARP_UI_SERVICE,
        }
        self.commands = {**self.commands}

    def _get_dashboard_executable(self, processes):
        # todo make sure the frontend tools are available, in the right versions
        if not os.path.exists(os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend/node_modules")):
            # todo better guidance
            raise click.UsageError(
                "Dashboard's frontend dependencies are not installed.\nYour options are: run a production version "
                "(shortcut to come), install the dependencies (with `harp install-dev`), or do not run the dashboard."
            )

        host = "localhost"

        return (
            os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend"),
            " ".join(
                [
                    "pnpm exec vite",
                    f"--host {host}",
                    f"--port {self.ports[HARP_DASHBOARD_SERVICE]}",
                    "--strictPort",
                    "--clearScreen false",
                ]
            ),
        )

    commands[HARP_DASHBOARD_SERVICE] = _get_dashboard_executable

    def _get_server_executable(self, processes):
        cmd = f"{sys.executable} -m harp server"
        proxy_options = list(self.proxy_options)

        if HARP_DASHBOARD_SERVICE in processes:
            proxy_options.append(f"--set dashboard.devserver.port={quote(self.ports[HARP_DASHBOARD_SERVICE])}")

        for _name, _port in self.proxy_ports.items():
            proxy_options.append(f"--endpoint {quote(_name)}={_port}:http://localhost:{self.ports[_name]}")

        if proxy_options:
            cmd += " " + " ".join(proxy_options)

        return (
            None,
            f'watchfiles --filter python "{cmd}" {os.path.join(ROOT_DIR, "harp")} {os.path.join(ROOT_DIR, "harp_apps")}',
        )

    commands[HARP_SERVER_SERVICE] = _get_server_executable

    def _get_docs_executable(self, processes):
        # todo add check available
        return (
            os.path.join(ROOT_DIR, "docs"),
            "poetry run sphinx-autobuild . _build/html",
        )

    commands[HARP_DOCS_SERVICE] = _get_docs_executable

    def _get_ui_executable(self, processes):
        # todo add check available
        return os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend"), "pnpm ui:serve"

    commands[HARP_UI_SERVICE] = _get_ui_executable

    def build(self, processes, /, *, more_env=None):
        from honcho.manager import Manager
        from honcho.printer import Printer

        manager = Manager(Printer(sys.stdout))
        for name in processes:
            if name not in self.commands:
                raise ValueError(f"Unknown process: {name}")

            if callable(self.commands[name]):
                working_directory, command = self.commands[name](self, processes)
            else:
                working_directory, command = (
                    self.cwds.get(name, None),
                    self.commands[name],
                )
                if working_directory is None:
                    working_directory = os.getcwd()
                else:
                    working_directory = os.path.join(os.getcwd(), working_directory)

            e = os.environ.copy()
            more_env = more_env or {}
            manager.add_process(name, command, cwd=working_directory, env=e | more_env.get(name, {}))

            logger.debug(f"Added process {name}: {command}")

            # this hack will change the class impl at runtime for frontend process to avoid misleading log at start.
            if name == HARP_DASHBOARD_SERVICE:
                from harp.commandline.utils._hacks import QuietViteHonchoProcess

                manager._processes[name]["obj"].__class__ = QuietViteHonchoProcess

        return manager


def parse_server_subprocesses_options(server_subprocesses):
    # TODO uniformise with --endpoint to be in format name=port:cmd
    processes = {}
    for server_subprocess in server_subprocesses:
        try:
            _name, _port, _path, _command = server_subprocess.split(":", 3)
        except ValueError as exc:
            raise click.UsageError(
                "Invalid server subprocess configuration. Expected format: <name>:<port>:<path>:<command>."
            ) from exc
        _target_port = get_available_network_port()
        _command = Template(_command).safe_substitute(port=_target_port)
        processes[_name] = (_port, _path, _command, _target_port)

    return processes
