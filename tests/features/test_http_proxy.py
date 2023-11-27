"""
Initial implementation : https://trello.com/c/yCdcY7Og/1-5-http-proxy
"""
import asyncio
import dataclasses

import pytest
from asgi_tools import App
from asgiref.testing import ApplicationCommunicator
from hypercorn import Config
from hypercorn.asyncio import serve
from hypercorn.typing import LifespanScope, LifespanStartupEvent

from harp.proxy import Proxy, ProxyFactory
from harp.testing.http_communiator import HttpCommunicator
from harp.testing.network_utils import get_available_network_port

app = App()


@app.route("/")
async def hello_world(request):
    return "<p>Hello, World!</p>"


@dataclasses.dataclass
class StubServerDescription:
    host: str
    port: int


@pytest.fixture
def stubd():
    port = get_available_network_port()
    loop = asyncio.get_event_loop()
    config = Config()
    config.bind = [f"localhost:{port}"]

    shutdown_event = asyncio.Event()

    async def do_serve():
        return await serve(app, config, shutdown_trigger=shutdown_event.wait)

    task = asyncio.ensure_future(do_serve(), loop=loop)
    loop.run_until_complete(asyncio.sleep(1))

    try:
        yield StubServerDescription("localhost", port)
    finally:
        shutdown_event.set()
        loop.run_until_complete(task)


class TestProxy(Proxy):
    def get(self, path, *, port=None):
        return HttpCommunicator(self, "GET", path, port=port)


class TestAsgiProxy:
    def create_proxy_factory(self, *args, **kwargs):
        return ProxyFactory(*args, ProxyType=TestProxy, **kwargs)

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_no_endpoint(self):
        proxy = self.create_proxy_factory().create()
        response = await proxy.get("/").get_response()
        assert response["status"] == 404
        assert response["body"] == b"No endpoint found for port 80."
        assert response["headers"] == []

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_basic(self, stubd):
        proxy_factory = self.create_proxy_factory()
        proxy_factory.add(f"http://{stubd.host}:{stubd.port}", port=stubd.port, name="default")
        proxy = proxy_factory.create()
        com = ApplicationCommunicator(proxy, LifespanScope(type="lifespan", asgi={"version": "2.0"}))
        await com.send_input(LifespanStartupEvent(type="lifespan.startup"))
        await com.wait()
        response = await proxy.get("/", port=stubd.port).get_response()
        assert response["status"] == 200
        assert response["body"] == b"<p>Hello, World!</p>"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)
