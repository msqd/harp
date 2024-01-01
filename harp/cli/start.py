import os
import re
import sys
from itertools import chain
from string import Template

import rich_click as click
from colorama import Fore
from honcho.process import Process

from harp import ROOT_DIR
from harp.utils.network import get_available_network_port


class QuietViteHonchoProcess(Process):
    _muted = True
    _status = ""

    def _send_message(self, data, type="line"):
        if type == "line" and self._muted:
            if b"  VITE v" in data:
                self._status = data.decode("utf-8").strip()

            if b"Local:   http://localhost:" in data:
                url = re.search("(?P<url>https?://[^\s]+)", data.decode("utf-8")).group("url")
                super()._send_message(
                    (
                        "📈  "
                        + Fore.LIGHTBLUE_EX
                        + "Dashboard development server started."
                        + Fore.RESET
                        + (f" ({self._status})" if self._status else "")
                    ).encode(),
                )
                super()._send_message(("  ➜ Internal url: " + url).encode())
                super()._send_message(
                    "  ➜ This url is for internal use only, you should use the proxied url instead.".encode()
                )

            if b"press h + enter to show help" in data:
                self._muted = False
            return

        return super()._send_message(data, type)


class HonchoManagerFactory:
    names = {"frontend", "proxy", "docs", "ui"}
    defaults = {"frontend", "proxy"}

    def __init__(self, *, proxy_options=()):
        self.ports = {"frontend": get_available_network_port()}
        self.proxy_ports = {}
        self.proxy_options = proxy_options
        self.commands = {}

    def get_frontend_executable(self, processes):
        # todo make sure the frontend tools are available, in the right versions
        if not os.path.exists(os.path.join(ROOT_DIR, "frontend/node_modules")) or not os.path.exists(
            os.path.join(ROOT_DIR, "vendors/mkui/node_modules")
        ):
            # todo better guidance
            raise click.UsageError(
                "Dashboard's frontend dependencies are not installed.\nYour options are: run a production version "
                "(shortcut to come), install the dependencies (with `harp install-dev`), or do not run the dashboard."
            )

        return f"(cd frontend; pnpm exec vite --host 'localhost' --port {self.ports['frontend']} --strictPort --clearScreen false)"

    def get_proxy_executable(self, processes):
        cmd = f"{sys.executable} bin/entrypoint"
        proxy_options = list(self.proxy_options)

        if "frontend" in processes:
            proxy_options.append(f"--set dashboard.devserver_port {self.ports['frontend']}")

        for _name, _port in self.proxy_ports.items():
            proxy_options.append(f"--set proxy.endpoints.{_port}.name {_name}")
            proxy_options.append(f"--set proxy.endpoints.{_port}.url http://localhost:{self.ports[_name]}")

        if proxy_options:
            cmd += " " + " ".join(proxy_options)

        return f'watchfiles --filter python "{cmd}" harp'

    def get_docs_executable(self, processes):
        # todo add check available
        return "(cd docs; sphinx-autobuild . _build/html)"

    def get_ui_executable(self, processes):
        # todo add check available
        return "(cd vendors/mkui; pnpm serve)"

    def build(self, processes) -> "honcho.Manager":
        from honcho.manager import Manager
        from honcho.printer import Printer

        manager = Manager(Printer(sys.stdout))
        for name in processes:
            if name in self.commands:
                command = self.commands[name]
            elif (method := getattr(self, f"get_{name}_executable", None)) is not None:
                command = method(processes)
            else:
                raise ValueError(f"Unknown process: {name}")

            e = os.environ.copy()
            manager.add_process(name, command, cwd=ROOT_DIR, env=e)

            # this hack will change the class impl at runtime for frontend process to avoid misleading log at start.
            if name == "frontend":
                manager._processes[name]["obj"].__class__ = QuietViteHonchoProcess

        return manager


def _parse_subprocesses(server_subprocesses):
    processes = {}
    for server_subprocess in server_subprocesses:
        _name, _port, _command = server_subprocess.split(":", 2)
        _target_port = get_available_network_port()
        _command = Template(_command).substitute(port=_target_port)
        processes[_name] = (_port, _command, _target_port)
    return processes


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
    help="Add a server subprocess to the list of processes to start.",
)
@click.argument("services", nargs=-1)
def start(with_docs, with_ui, options, files, services, server_subprocesses):
    try:
        # todo check watchfiles too ?
        from honcho.manager import Manager
        from honcho.printer import Printer
    except ImportError as exc:
        # todo when released on pypi, add more help
        raise click.UsageError(
            "You must install development dependencies to start the development environment.\n"
            + "\n"
            + 'Try to install the "dev" extra.'
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

    processes = {"frontend", "proxy"}
    if with_docs or "docs" in services:
        processes.add("docs")
    if with_ui or "ui" in services:
        processes.add("ui")

    for _name, (_proxy_port, _cmd, _port) in _parse_subprocesses(server_subprocesses).items():
        processes.add(_name)
        manager_factory.proxy_ports[_name] = _proxy_port
        manager_factory.ports[_name] = _port
        manager_factory.commands[_name] = _cmd

    # allow to limit the services to start
    if services:
        unknown_services = set(services) - processes
        if unknown_services:
            raise click.UsageError(f"Unknown services: {', '.join(unknown_services)}")

    manager = manager_factory.build(processes)
    manager.loop()
    sys.exit(manager.returncode)
