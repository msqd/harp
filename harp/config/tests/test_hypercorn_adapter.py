"""The hypercorn adapter cuts a client that goes silent mid-request, and lets a slow but live one finish."""

import asyncio
from types import SimpleNamespace

import pytest

from harp.config.adapters.hypercorn import HypercornAdapter
from harp.settings import DEFAULT_CLIENT_READ_TIMEOUT
from harp.utils.network import Bind, get_available_network_port, wait_for_port
from harp_apps.proxy.settings import ProxySettings

TIMEOUT = 0.5
HEADERS = b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 4\r\nConnection: close\r\n\r\n"


async def asgi_app(scope, receive, send):
    if scope["type"] != "http":
        return
    message = await receive()
    while message.get("more_body"):
        message = await receive()
    if message["type"] == "http.disconnect":
        return
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-length", b"2")]})
    await send({"type": "http.response.body", "body": b"ok"})


def _system(port, config):
    return SimpleNamespace(binds=[Bind("127.0.0.1", port)], asgi_app=asgi_app, config=config)


@pytest.fixture
async def server():
    port = get_available_network_port()
    adapter = HypercornAdapter(_system(port, {"proxy": ProxySettings(client_read_timeout=TIMEOUT)}))
    task = asyncio.ensure_future(adapter.serve())
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    try:
        yield port
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_client_stalling_mid_body_is_disconnected(server):
    reader, writer = await asyncio.open_connection("127.0.0.1", server)
    writer.write(HEADERS + b"ab")
    await writer.drain()

    # the server hangs up after the timeout, well before the 5s guard
    assert await asyncio.wait_for(reader.read(), 5) == b""
    writer.close()


async def test_slow_upload_under_the_timeout_completes(server):
    reader, writer = await asyncio.open_connection("127.0.0.1", server)
    writer.write(HEADERS)
    for chunk in (b"a", b"b", b"c", b"d"):
        await writer.drain()
        await asyncio.sleep(TIMEOUT * 0.6)  # whole upload lasts longer than the timeout
        writer.write(chunk)
    await writer.drain()

    assert (await asyncio.wait_for(reader.read(), 5)).startswith(b"HTTP/1.1 200")
    writer.close()


def test_read_timeout_defaults_to_the_documented_value():
    assert ProxySettings().client_read_timeout == DEFAULT_CLIENT_READ_TIMEOUT == 30.0
    adapter = HypercornAdapter(_system(8080, {"proxy": ProxySettings()}))
    assert adapter._create_hypercorn_config([]).read_timeout == 30.0


def test_read_timeout_falls_back_to_the_default_without_proxy_settings():
    adapter = HypercornAdapter(_system(8080, {}))
    assert adapter._create_hypercorn_config([]).read_timeout == DEFAULT_CLIENT_READ_TIMEOUT
