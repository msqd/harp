"""A client trickling its request body is answered 408 and never forwarded upstream (#1220), through real servers."""

import asyncio

import httpx
import pytest
from hypercorn.asyncio import serve
from hypercorn.config import Config

from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote

GRACE = 1.0  # seconds, scaled down from the 10 s default
MIN_RATE = 1024  # bytes per second


class Origin:
    def __init__(self):
        self.bodies = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while (await receive())["type"] != "lifespan.shutdown":
                await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
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
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    servers = [await _serve(origin, origin_port, shutdown), await _serve(kernel, proxy_port, shutdown)]
    try:
        yield origin, proxy_port
    finally:
        shutdown.set()
        await asyncio.gather(*servers)


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
