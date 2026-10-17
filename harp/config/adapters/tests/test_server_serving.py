import asyncio
from types import SimpleNamespace

import httpx
import pytest

from harp.config.adapters import SERVERS, get_server
from harp.utils.network import Bind, get_available_network_port, wait_for_port


class Lifespan:
    def __init__(self):
        self.events = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                self.events.append(message["type"])
                await send({"type": message["type"] + ".complete"})
                if message["type"] == "lifespan.shutdown":
                    return
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"hello"})


@pytest.mark.parametrize("name", SERVERS)
async def test_serves_a_request_in_process(name):
    app = Lifespan()
    ports = [get_available_network_port(), get_available_network_port()]
    system = SimpleNamespace(binds=[Bind("127.0.0.1", port) for port in ports], asgi_app=app)
    adapter = get_server(name).adapter_type(system)

    task = asyncio.ensure_future(adapter.serve())
    try:
        for port in ports:
            await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://127.0.0.1:{port}/")
            assert (response.status_code, response.text) == (200, "hello")
        assert app.events == ["lifespan.startup"]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
