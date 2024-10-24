import asyncio
import dataclasses
from asyncio import get_running_loop

import pytest  # noqa
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.stub_api import stub_api
from harp_apps.storage.conftest import *  # noqa


@dataclasses.dataclass
class StubServerDescription:
    host: str
    port: int

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


@pytest.fixture
async def test_api():
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
        loop=get_running_loop(),
    )
    await asyncio.to_thread(wait_for_port, port, host)

    try:
        yield StubServerDescription(host, port)
    finally:
        shutdown_event.set()
        await server
