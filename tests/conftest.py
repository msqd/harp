import asyncio
import dataclasses

import pytest
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.utils.network import get_available_network_port
from harp.utils.testing.stub_api import stub_api


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
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_api(event_loop):
    shutdown_event = asyncio.Event()
    config = Config()
    port = get_available_network_port()
    config.bind = [f"localhost:{port}"]

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
    await asyncio.open_connection("localhost", port)

    try:
        yield StubServerDescription("localhost", port)
    finally:
        shutdown_event.set()
        await server
