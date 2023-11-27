import asyncio
import dataclasses

import pytest
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.testing.network_utils import get_available_network_port
from harp.testing.stub_api import stub_api


@dataclasses.dataclass
class StubServerDescription:
    host: str
    port: int


@pytest.fixture
def stub_api_server():
    port = get_available_network_port()
    loop = asyncio.get_event_loop()
    config = Config()
    config.bind = [f"localhost:{port}"]

    shutdown_event = asyncio.Event()

    async def do_serve():
        return await serve(stub_api, config, shutdown_trigger=shutdown_event.wait)

    task = asyncio.ensure_future(do_serve(), loop=loop)
    # TODO: find a better way to wait for the server to be ready
    loop.run_until_complete(asyncio.sleep(1))

    try:
        yield StubServerDescription("localhost", port)
    finally:
        shutdown_event.set()
        loop.run_until_complete(task)
