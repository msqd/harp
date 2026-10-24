import click
import pytest
from click import Context, UsageError
from click.testing import CliRunner

from harp.commandline.options.server import _EnhancedParserCommand
from harp.commandline.server import CommonServerOptions, server
from harp.commandline.system import config_subcommand, services_subcommand


def test_default():
    options = CommonServerOptions(options=(), files=(), enable=(), disable=())
    assert options.as_list() == []


def test_applications():
    options = CommonServerOptions(options=(), files=(), enable=("foo", "bar"), disable=("baz", "blurp"))
    assert options.as_list() == [
        "--enable foo",
        "--enable bar",
        "--disable baz",
        "--disable blurp",
    ]


def test_parse_args_default_behaviour():
    @click.command(cls=_EnhancedParserCommand)
    @click.option("--other")
    def cmd(): ...

    assert _call_command(cmd, "--other", "value") == {"other": "value"}
    with pytest.raises(UsageError):
        _call_command(cmd, "--other", "value", "unknown")


def test_parse_args_set_behaviour():
    @click.command(cls=_EnhancedParserCommand)
    @click.option("--set", "options", multiple=True, type=(str, str))
    def cmd(): ...

    assert _call_command(cmd, "--set", "arg=value", "--set", "foo", "bar") == {
        "options": (("arg", "value"), ("foo", "bar"))
    }


@pytest.mark.parametrize("command", [config_subcommand, services_subcommand])
def test_system_commands_parse_equals_form_of_set(command):
    assert _call_command(command, "--set", "dashboard.port=8080")["options"] == (("dashboard.port", "8080"),)


@pytest.mark.parametrize("command", [config_subcommand, server])
@pytest.mark.parametrize(
    "args",
    [
        ("--set", "storage.url=postgresql://host/db?sslmode=require"),
        ("--set", "storage.url", "postgresql://host/db?sslmode=require"),
    ],
)
def test_server_commands_keep_equals_in_set_values(command, args):
    assert _call_command(command, *args)["options"] == (("storage.url", "postgresql://host/db?sslmode=require"),)


@pytest.mark.parametrize("command", [config_subcommand, server])
def test_server_commands_render_rich_help(command):
    result = CliRunner().invoke(command, ["--help"])

    assert result.exit_code == 0
    assert "--set" in result.output
    assert "[code]" not in result.output


def test_parse_args_mixed_arguments_behaviour():
    @click.command(cls=_EnhancedParserCommand)
    @click.option("--foo")
    @click.option("--bar")
    @click.option("--set", "options", multiple=True, type=(str, str))
    @click.argument("positional", nargs=-1)
    def cmd(): ...

    assert _call_command(
        cmd,
        "--foo",
        "foo",
        "something",
        "--set",
        "arg=value",
        "completely",
        "--set",
        "foo",
        "bar",
        "different",
        "--bar",
        "bar",
    ) == {
        "foo": "foo",
        "bar": "bar",
        "options": (("arg", "value"), ("foo", "bar")),
        "positional": ("something", "completely", "different"),
    }


def _call_command(cmd, *args):
    ctx = Context(cmd)
    cmd.parse_args(ctx, list(args))
    return ctx.params


def test_as_list_quotes_every_value():
    import shlex

    nasty = "x; touch /tmp/pwned $(id) `id` 'q' \"d\""
    options = CommonServerOptions(
        options=(),
        endpoints=(f"{nasty}=4000:http://localhost/",),
        files=(nasty,),
        examples=(nasty,),
        enable=(nasty,),
        disable=(nasty,),
    )

    argv = shlex.split(" ".join(options.as_list()))

    assert argv == [
        "--endpoint",
        f"{nasty}=4000:http://localhost/",
        "--enable",
        nasty,
        "--disable",
        nasty,
        "--file",
        nasty,
        "--example",
        nasty,
    ]


def test_set_values_parsed_as_non_strings_reach_the_command():
    import shlex

    options = CommonServerOptions(options=(("x", "true"), ("y", "false"), ("n", "3")))

    argv = shlex.split(" ".join(options.as_list()))

    assert argv == ["--set", "x=true", "--set", "y=false", "--set", "n=3"]
