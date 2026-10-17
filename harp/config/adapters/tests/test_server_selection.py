import sys

import pytest
from click.testing import CliRunner

from harp.commandline.options.server import CommonServerOptions
from harp.commandline.server import server
from harp.config.adapters import DEFAULT_SERVER, SERVERS, get_server
from harp.config.adapters.granian import GranianAdapter
from harp.config.adapters.hypercorn import HypercornAdapter
from harp.config.adapters.uvicorn import UvicornAdapter


def test_default_is_hypercorn():
    assert DEFAULT_SERVER == "hypercorn"
    assert get_server(DEFAULT_SERVER).adapter_type is HypercornAdapter


@pytest.mark.parametrize(
    "name, adapter_type, uvloop",
    [
        ("hypercorn", HypercornAdapter, False),
        ("hypercorn+uvloop", HypercornAdapter, True),
        ("uvicorn", UvicornAdapter, True),
        ("granian", GranianAdapter, False),
    ],
)
def test_names_select_adapter(name, adapter_type, uvloop):
    adapter = get_server(name)
    assert adapter.adapter_type is adapter_type
    assert adapter.uvloop is uvloop


def test_every_server_is_selectable():
    for name in SERVERS:
        get_server(name)


def test_unknown_server_fails_clearly():
    with pytest.raises(ValueError, match=r"Unknown server 'nope'.*hypercorn.*uvicorn.*granian"):
        get_server("nope")


def test_option_default_is_not_forwarded_to_subprocess():
    assert CommonServerOptions().as_list() == []


def test_option_forwarded_to_subprocess():
    assert CommonServerOptions(server="uvicorn").as_list() == ["--server uvicorn"]


def test_command_rejects_unknown_server():
    result = CliRunner().invoke(server, ["--server", "nope"])
    assert result.exit_code == 2
    assert "nope" in result.output


def test_command_reads_server_from_environment(monkeypatch):
    seen = {}
    module = sys.modules["harp.commandline.server"]  # the package attribute is shadowed by the command
    monkeypatch.setattr(module, "run", lambda builder, server: seen.update(server=server))
    monkeypatch.setattr(
        module,
        "get_configuration_builder_type",
        lambda: type("B", (), {"from_commandline_options": staticmethod(lambda options: object())}),
    )
    result = CliRunner().invoke(server, [], env={"HARP_SERVER": "granian"})
    assert result.exit_code == 0, result.output
    assert seen == {"server": "granian"}
