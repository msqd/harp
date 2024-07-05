import asyncio
import dataclasses

import pytest  # noqa
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.utils.network import get_available_network_port
from harp.utils.testing.stub_api import stub_api
from harp_apps.storage.conftest import *  # noqa


@dataclasses.dataclass
class StubServerDescription:
    host: str
    port: int

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
async def test_api(event_loop):
    shutdown_event = asyncio.Event()
    config = Config()
    host, port = "127.0.0.1", get_available_network_port()
    config.bind = [f"{host}:{port}"]

    # starts the async server in the background
    server = asyncio.ensure_future(
        serve(
            stub_api,
            config=config,
            shutdown_trigger=shutdown_event.wait,
        ),
        loop=event_loop,
    )
    # wait for the server to be accepting connections
    await asyncio.open_connection(host, port)

    try:
        yield StubServerDescription(host, port)
    finally:
        shutdown_event.set()
        await server
