import asyncio

import h2.config
import h2.connection
import h2.events
import pytest
from hypercorn import Config
from hypercorn.asyncio import serve

from harp.asgi.kernel import ASGIKernel
from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator


async def _call(kernel, raw_path: bytes) -> dict:
    scope = {
        "type": "http",
        "http_version": "2",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": raw_path,
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await kernel(scope, receive, send)
    return sent[0]


class TestKernelRejectedRequest:
    @pytest.fixture
    async def kernel(self):
        kernel = ASGIKernel()
        await ASGICommunicator(kernel).asgi_lifespan_startup()
        return kernel

    @pytest.mark.asyncio
    async def test_non_utf8_path_gets_400_then_next_request_is_served(self, kernel):
        assert (await _call(kernel, b"/\xff"))["status"] == 400
        assert (await _call(kernel, b"/"))["status"] == 404


async def _h2c_status(port: int, path: bytes) -> int | None:
    reader, writer = await asyncio.open_connection("localhost", port)
    conn = h2.connection.H2Connection(
        config=h2.config.H2Configuration(client_side=True, validate_outbound_headers=False)
    )
    conn.initiate_connection()
    conn.send_headers(
        1,
        [(b":method", b"GET"), (b":path", path), (b":scheme", b"http"), (b":authority", b"localhost")],
        end_stream=True,
    )
    writer.write(conn.data_to_send())
    await writer.drain()

    status = None
    try:
        while status is None:
            data = await asyncio.wait_for(reader.read(65535), 5)
            if not data:
                break
            for event in conn.receive_data(data):
                if isinstance(event, h2.events.ResponseReceived):
                    status = int(dict(event.headers)[b":status"])
            writer.write(conn.data_to_send())
    finally:
        writer.close()
    return status


class TestH2cNonUtf8Path:
    @pytest.mark.asyncio
    async def test_non_utf8_path_never_reaches_the_app_and_server_keeps_serving(self):
        """hypercorn refuses non-ASCII ``:path`` bytes itself (connection dropped, no response), before the app."""
        kernel = ASGIKernel()
        await ASGICommunicator(kernel).asgi_lifespan_startup()

        shutdown = asyncio.Event()
        port = get_available_network_port()
        config = Config()
        config.bind = [f"localhost:{port}"]
        server = asyncio.ensure_future(serve(kernel, config=config, shutdown_trigger=shutdown.wait))
        await asyncio.to_thread(wait_for_port, port, "localhost")
        try:
            assert await _h2c_status(port, b"/\xff") is None
            assert await _h2c_status(port, b"/") == 404
        finally:
            shutdown.set()
            await server
