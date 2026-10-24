"""A client trickling or stalling its request body is answered 408 and never forwarded upstream (#1220), and a slow
response is not cut (#1245), through real servers, the proxy being served by the hypercorn adapter."""

import asyncio

import httpx
import pytest
from types import SimpleNamespace
from hypercorn.asyncio import serve
from hypercorn.config import Config

from harp.asgi import ASGIKernel
from harp.config.adapters.hypercorn import HypercornAdapter
from harp.controllers import DefaultControllerResolver
from harp.utils.network import Bind, get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings import ProxySettings
from harp_apps.proxy.settings.remote import Remote

GRACE = 3.0  # seconds, scaled down from the 10 s default
MIN_RATE = 1024  # bytes per second
IDLE = 1.0  # seconds of silence, scaled down from the 30 s default


class Origin:
    def __init__(self):
        self.bodies = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while (await receive())["type"] != "lifespan.shutdown":
                await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
            return
        if scope["path"] == "/slow-response":  # streams for longer than IDLE
            await send({"type": "http.response.start", "status": 200, "headers": []})
            for _ in range(8):
                await asyncio.sleep(0.4)
                await send({"type": "http.response.body", "body": b"chunk", "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        self.bodies.append(body)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})


async def _serve(app, port, shutdown):
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    server = asyncio.ensure_future(serve(app, config=config, shutdown_trigger=shutdown.wait))
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    return server


@pytest.fixture
async def stack():
    origin, shutdown = Origin(), asyncio.Event()
    origin_port, proxy_port = get_available_network_port(), get_available_network_port()
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": f"http://127.0.0.1:{origin_port}/"}]}),
        http_client=httpx.AsyncClient(),
        name="api",
        min_request_body_rate=MIN_RATE,
        request_body_grace_period=GRACE,
        client_read_timeout=IDLE,
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    system = SimpleNamespace(
        binds=[Bind("127.0.0.1", proxy_port)],
        asgi_app=kernel,
        config={"proxy": ProxySettings(client_read_timeout=IDLE)},
    )
    proxy = asyncio.ensure_future(HypercornAdapter(system).serve())
    servers = [await _serve(origin, origin_port, shutdown)]
    await asyncio.to_thread(wait_for_port, proxy_port, "127.0.0.1")
    try:
        yield origin, proxy_port
    finally:
        proxy.cancel()
        shutdown.set()
        await asyncio.gather(proxy, *servers, return_exceptions=True)


@pytest.mark.parametrize("interval", [0.6, 0.3])
async def test_trickling_client_gets_408_and_is_not_forwarded(stack, interval):
    origin, port = stack
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 1048576\r\n\r\n")

    async def trickle():
        try:
            while True:
                writer.write(b"x")
                await writer.drain()
                await asyncio.sleep(interval)
        except ConnectionError:
            pass

    task = asyncio.ensure_future(trickle())
    try:
        response = await asyncio.wait_for(reader.read(), 10)
    finally:
        task.cancel()
        writer.close()

    assert response.startswith(b"HTTP/1.1 408")
    assert origin.bodies == []


async def test_slow_upload_above_the_minimum_rate_completes(stack):
    origin, port = stack
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    chunk, count = b"x" * 400, 12  # 4 KiB/s for over 2 s, longer than the grace period
    writer.write(f"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: {len(chunk) * count}\r\n\r\n".encode())
    for _ in range(count):
        writer.write(chunk)
        await writer.drain()
        await asyncio.sleep(0.1)
    # first request of the connection, no keep-alive wait: read the head of the answer
    response = await asyncio.wait_for(reader.read(12), 10)
    writer.close()

    assert response.startswith(b"HTTP/1.1 200")
    assert origin.bodies == [chunk * count]


async def test_client_silent_mid_body_gets_408_and_is_not_forwarded(stack):
    origin, port = stack
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 1048576\r\n\r\nabc")
    loop = asyncio.get_running_loop()
    start = loop.time()

    response = await asyncio.wait_for(reader.read(), 10)
    writer.close()

    assert response.startswith(b"HTTP/1.1 408")
    assert IDLE <= loop.time() - start < GRACE  # cut by the silence timeout, not by the minimum rate
    assert origin.bodies == []


async def test_response_streaming_longer_than_the_silence_timeout_completes(stack):
    _, port = stack
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET /slow-response HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")  # then silent for 3 s

    response = await asyncio.wait_for(reader.read(), 10)
    writer.close()

    assert response.startswith(b"HTTP/1.1 200")
    assert response.count(b"5\r\nchunk") == 8
