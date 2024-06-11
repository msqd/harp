from dataclasses import dataclass, field
from itertools import chain
from shlex import quote
from typing import Iterable

from harp.utils.commandline import click, code


@dataclass(kw_only=True)
class CommonServerOptions(dict):
    """
    Common server options, in a dataclass.
    """

    options: dict = field(default_factory=dict)
    endpoints: Iterable = field(default_factory=dict)
    files: tuple = ()
    enable: tuple = ()
    disable: tuple = ()

    # TODO maybe run reset as a pre-start command, so it does not run on each reload?
    reset: bool = False

    def as_list(self):
        return list(
            chain(
                (f"--set {quote(key)}={quote(value)}" for key, value in self.options.items()),
                (f"--endpoint {quote(key)}={quote(value)}" for key, value in self.endpoints.items()),
                ("--enable {app}".format(app=app) for app in self.enable),
                ("--disable {app}".format(app=app) for app in self.disable),
                ("--file " + file for file in self.files),
                (("--set storage.drop_tables=true",) if self.reset else ()),
            )
        )

    def __post_init__(self):
        self.options = dict(map(lambda x: x.split("=", 1), self.options))
        self.endpoints = dict(map(lambda x: x.split("=", 1), self.endpoints))


def add_harp_server_click_options(f):
    """
    Decorate a click command to add common server options, in the right order.
    """
    options = [
        click.option(
            "--set",
            "options",
            multiple=True,
            help=f"Set proxy configuration options (e.g. {code('--set foo=bar')}, can be used multiple times).",
        ),
        click.option(
            "--endpoint",
            "endpoints",
            multiple=True,
            help=f"""Add an endpoint (e.g. {code('--endpoint httpbin=4000:http://httpbin.org/')}, can be used multiple
            times).""",
        ),
        click.option(
            "--file",
            "-f",
            "files",
            default=(),
            multiple=True,
            help="""Load configuration from file (configuration format will be detected from file extension, can be
            used multiple times).""",
        ),
        click.option("--enable", default=(), multiple=True, help="Enable some applications."),
        click.option("--disable", default=(), multiple=True, help="Disable some applications."),
    ]

    # apply options in reversed order so that click will apply them in the right order (it's intended to be used as a
    # decorator, hence the reversal).
    for option in reversed(options):
        f = option(f)

    return f
