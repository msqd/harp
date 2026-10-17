import sys

import pytest
from click.testing import CliRunner
from httpx import AsyncClient, AsyncHTTPTransport

from harp.commandline.options.server import CommonServerOptions
from harp.commandline.server import server
from harp.config import ConfigurationBuilder
from harp_apps.http_client.aiohttp_transport import AiohttpTransport
from harp_apps.http_client.clients import CLIENTS, DEFAULT_CLIENT, get_client


def test_default_is_httpx():
    assert DEFAULT_CLIENT == "httpx"
    assert get_client(DEFAULT_CLIENT).transport_type == "httpx.AsyncHTTPTransport"


def test_every_client_is_selectable():
    assert CLIENTS == ("httpx", "aiohttp")
    for name in CLIENTS:
        get_client(name)


def test_unknown_client_fails_clearly():
    with pytest.raises(ValueError, match=r"Unknown client 'nope'.*httpx.*aiohttp"):
        get_client("nope")


def test_option_default_is_not_forwarded_to_subprocess():
    assert CommonServerOptions().as_list() == []


def test_option_forwarded_to_subprocess():
    assert CommonServerOptions(client="aiohttp").as_list() == ["--client aiohttp"]


def test_command_rejects_unknown_client():
    result = CliRunner().invoke(server, ["--client", "nope"])
    assert result.exit_code == 2
    assert "nope" in result.output


def test_command_reads_client_from_environment(monkeypatch):
    seen = {}
    module = sys.modules["harp.commandline.server"]  # the package attribute is shadowed by the command
    monkeypatch.setattr(module, "run", lambda builder, **kwargs: None)
    monkeypatch.setattr(
        module,
        "get_configuration_builder_type",
        lambda: type("B", (), {"from_commandline_options": staticmethod(lambda options: seen.update(o=options))}),
    )
    result = CliRunner().invoke(server, [], env={"HARP_CLIENT": "aiohttp"})
    assert result.exit_code == 0, result.output
    assert seen["o"].client == "aiohttp"


async def underlying_transport(**options):
    """The transport under the proxy filter, as the application builds it from the command line options."""
    builder = ConfigurationBuilder.from_commandline_options(
        CommonServerOptions(applications=("http_client",), **options)
    )
    system = await builder.abuild_system(validate_dependencies=False)
    try:
        return system.provider.get(AsyncClient)._transport._transport
    finally:
        await system.dispose()


async def test_aiohttp_client_swaps_what_is_under_the_proxy_transport():
    assert isinstance(await underlying_transport(client="aiohttp"), AiohttpTransport)


async def test_default_client_is_httpx():
    assert isinstance(await underlying_transport(), AsyncHTTPTransport)


async def test_explicit_transport_setting_wins_over_the_client_option():
    options = (("http_client.transport.type", "httpx.AsyncHTTPTransport"),)
    assert isinstance(await underlying_transport(client="aiohttp", options=options), AsyncHTTPTransport)
