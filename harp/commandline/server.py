from dataclasses import dataclass, field
from itertools import chain
from shlex import quote
from typing import Iterable

from harp.utils.commandline import click


@dataclass(kw_only=True)
class ServerOptions(dict):
    options: Iterable = field(default_factory=dict)
    endpoints: Iterable = field(default_factory=dict)
    files: tuple = ()
    enable: tuple = ()
    disable: tuple = ()
    reset: bool = False

    def as_list(self):
        return list(
            chain(
                (f"--set {quote(key)}={quote(value)}" for key, value in self.options.items()),
                (f"--endpoint {quote(key)}={quote(value)}" for key, value in self.endpoints.items()),
                ("--enable {app}".format(app=app) for app in self.enable),
                ("--disable {app}".format(app=app) for app in self.disable),
                ("--file " + file for file in self.files),
                (("--set storage.drop_tables true",) if self.reset else ()),
            )
        )

    def __post_init__(self):
        self.options = dict(map(lambda x: x.split("=", 1), self.options))
        self.endpoints = dict(map(lambda x: x.split("=", 1), self.endpoints))


def add_harp_server_click_options(f):
    f = click.option("--set", "options", multiple=True, help="Set proxy configuration options.")(f)
    f = click.option("--endpoint", "endpoints", multiple=True, help="Add an endpoint.")(f)
    f = click.option("--file", "-f", "files", default=(), multiple=True, help="Load configuration from file.")(f)
    f = click.option("--enable", default=(), multiple=True, help="Enable some applications.")(f)
    f = click.option("--disable", default=(), multiple=True, help="Disable some applications.")(f)
    f = click.option("--reset", is_flag=True, help="Reset the database (drop and recreate tables).")(f)
    return f


@click.command(short_help="Starts harp proxy server.")
@add_harp_server_click_options
def server(**kwargs):
    options = ServerOptions(**kwargs)

    from harp import Config, run

    config = Config()
    config.add_defaults()
    config.read_env(options)

    return run(config)
