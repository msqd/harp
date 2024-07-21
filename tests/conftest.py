import asyncio
import dataclasses

import pytest
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.utils.network import get_available_network_port, wait_for_port
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
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
async def test_api(event_loop):
    shutdown_event = asyncio.Event()
    config = Config()
    host, port = "localhost", get_available_network_port()
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
    await asyncio.to_thread(wait_for_port, port, host, 10.0)

    try:
        yield StubServerDescription(host, port)
    finally:
        shutdown_event.set()
        await server
