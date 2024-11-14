from dataclasses import dataclass, field
from itertools import chain
from shlex import quote
from typing import Any, Callable, Iterable, List, Optional, Type, Union

from click import Command
from click.decorators import CmdType

from harp.utils.commandline import click, code


@dataclass(kw_only=True)
class ConfigOptions:
    files: tuple = ()
    examples: tuple = ()
    options: dict = field(default_factory=dict)

    def __post_init__(self):
        self.options = dict(map(lambda x: x.split("=", 1), self.options))


def _parse_option(option: tuple[str, str]) -> tuple[str, Union[str, bool]]:
    key, value = option
    if value == "true":
        value = True
    elif value == "false":
        value = False
    return key, value


@dataclass(kw_only=True)
class CommonServerOptions(dict):
    """
    Common server options, in a dataclass.
    """

    options: dict = field(default_factory=dict)
    endpoints: Iterable = field(default_factory=dict)
    files: tuple = ()
    examples: tuple = ()

    applications: tuple = ()
    enable: tuple = ()
    disable: tuple = ()

    def as_list(self):
        return list(
            chain(
                (f"--set {quote(key)}={quote(value)}" for key, value in self.options.items()),
                (f"--endpoint {quote(key)}={quote(value)}" for key, value in self.endpoints.items()),
                ("--enable {app}".format(app=app) for app in self.enable),
                ("--disable {app}".format(app=app) for app in self.disable),
                ("--file " + file for file in self.files),
                ("--example " + example for example in self.examples),
            )
        )

    def __post_init__(self):
        self.options = dict(map(_parse_option, self.options))
        self.endpoints = dict(map(lambda x: x.split("=", 1), self.endpoints))


def _config_click_options(f):
    """
    Decorate a click command to add configuration options, in the right order.
    """
    options = [
        click.option(
            "--file",
            "-f",
            "files",
            default=(),
            multiple=True,
            type=click.Path(exists=True, dir_okay=False),
            help="""Load configuration from file (configuration format will be detected from file extension, can be
            used multiple times).""",
        ),
        click.option(
            "--example",
            "examples",
            default=(),
            multiple=True,
            help="""Load configuration from example (can be used multiple times).""",
        ),
        click.option(
            "--set",
            "options",
            multiple=True,
            type=(str, str),
            help=f"Add configuration options (e.g. {code('--set foo=bar')} or {code('--set foo bar')}, can be used multiple times).",
        ),
    ]

    # apply options in reversed order so that click will apply them in the right order (it's intended to be used as a
    # decorator, hence the reversal).
    for option in reversed(options):
        f = option(f)

    return f


def _server_click_options(f):
    """
    Decorate a click command to add common server options, in the right order.
    """
    options = [
        click.option(
            "--endpoint",
            "endpoints",
            multiple=True,
            help=f"""Add an endpoint (e.g. {code("--endpoint httpbin=4000:http://httpbin.org/")}, can be used multiple
            times).""",
        ),
        click.option(
            "--applications",
            default=None,
            type=click.STRING,
            help="List of applications to enable.",
            callback=lambda ctx, param, value: value.split(",") if value else (),
        ),
        click.option("--enable", default=(), multiple=True, help="Enable some applications."),
        click.option("--disable", default=(), multiple=True, help="Disable some applications."),
    ]

    # apply options in reversed order so that click will apply them in the right order (it's intended to be used as a
    # decorator, hence the reversal).
    for option in reversed(options):
        f = option(f)

    f = _config_click_options(f)

    return f


class _EnhancedParserCommand(click.Command):
    """
    This class override parse_args click function parse args enter in cli when type command with space or = for  --set
    command:

    eg: --set arg=value or arg value
    """

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        index = 0
        while index < len(args):
            if args[index] == "--set":
                if index + 1 < len(args):
                    # if an equal sign is present, we expand the argument into two separated arguments
                    if "=" in args[index + 1]:
                        args = args[: index + 1] + args[index + 1].split("=") + args[index + 2 :]
                        index += 1
            index += 1
        return super().parse_args(ctx, args)


def server_command(
    name: Union[Optional[str], Callable[..., Any]] = None,
    cls: Type[CmdType] = _EnhancedParserCommand,
    **attrs: Any,
) -> Union[Command, Callable[[Callable[..., Any]], Union[Command, CmdType]]]:
    """
    Creates a click command with server options (--enable, --disable, --applications, --endpoint and all configuration
    options).
    """

    def decorator(f: [Callable[..., Any]]) -> CmdType:
        command_decorator = click.command(name=name, cls=cls, **attrs)
        f = _server_click_options(f)
        f = command_decorator(f)
        return f

    return decorator


def config_command(
    name: Union[Optional[str], Callable[..., Any]] = None,
    cls: Type[CmdType] = _EnhancedParserCommand,
    **attrs: Any,
) -> Union[Command, Callable[[Callable[..., Any]], Union[Command, CmdType]]]:
    """
    Creates a click command with configuration options (--set, --example, --file).
    """

    def decorator(f: [Callable[..., Any]]) -> CmdType:
        command_decorator = click.command(name=name, cls=cls, **attrs)
        f = _config_click_options(f)
        f = command_decorator(f)
        return f

    return decorator
