import asyncio
import os
import signal
from types import SimpleNamespace

import httpx
import pytest

from harp.config.adapters import SERVERS, get_server
from harp.utils.network import Bind, get_available_network_port, wait_for_port


class Lifespan:
    def __init__(self):
        self.events = []
        self.server_ports = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                self.events.append(message["type"])
                await send({"type": message["type"] + ".complete"})
                if message["type"] == "lifespan.shutdown":
                    return
        self.server_ports.append(scope["server"][1])
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"hello"})


class PlainCallMiddleware:
    """Like the metrics application's middleware: a plain (non-async) ``__call__`` returning an awaitable."""

    def __init__(self, app):
        self.app = app

    def __call__(self, scope, receive, send):
        return self.app(scope, receive, send)


@pytest.mark.parametrize("wrap", [False, True], ids=["app", "plain-call-middleware"])
@pytest.mark.parametrize("host", ["127.0.0.1", "[::]"])
@pytest.mark.parametrize("name", SERVERS)
async def test_serves_a_request_in_process(name, host, wrap):
    app = Lifespan()
    ports = [get_available_network_port(), get_available_network_port()]
    system = SimpleNamespace(
        binds=[Bind(host, port) for port in ports], asgi_app=PlainCallMiddleware(app) if wrap else app
    )
    adapter = get_server(name).adapter_type(system)

    task = asyncio.ensure_future(adapter.serve())
    try:
        for port in ports:
            await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://127.0.0.1:{port}/")
            assert (response.status_code, response.text) == (200, "hello")
        assert app.events == ["lifespan.startup"]
        assert app.server_ports == ports  # ints, the way the controller resolver expects them
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("name", SERVERS)
async def test_returns_on_sigterm_so_the_system_can_be_disposed(name):
    port = get_available_network_port()
    system = SimpleNamespace(binds=[Bind("127.0.0.1", port)], asgi_app=Lifespan())
    adapter = get_server(name).adapter_type(system)

    task = asyncio.ensure_future(adapter.serve())
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    os.kill(os.getpid(), signal.SIGTERM)  # uvicorn would otherwise re-raise it once stopped, killing the process

    await asyncio.wait_for(task, timeout=10)
