"""A request with both Content-Length and Transfer-Encoding is neither forwarded nor recorded (#1426)."""

import asyncio

import httpx
from hypercorn.asyncio import serve
from hypercorn.config import Config
from whistle import AsyncEventDispatcher

from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote
from harp_apps.proxy.tests.test_aborted_upload import Origin
from harp_apps.storage.worker import StorageAsyncWorkerQueue

AMBIGUOUS = (
    b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n4\r\nabcd\r\n0\r\n\r\n"
)
VALID = b"GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"


async def _serve(app, port, shutdown):
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    server = asyncio.ensure_future(serve(app, config=config, shutdown_trigger=shutdown.wait))
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    return server


async def _raw(port, payload) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(payload)
    await writer.drain()
    data = await asyncio.wait_for(reader.read(), 10)
    writer.close()
    return data


async def test_ambiguous_framing_reaches_neither_upstream_nor_storage(sql_storage, blob_storage):
    origin, shutdown, dispatcher = Origin(), asyncio.Event(), AsyncEventDispatcher()
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, blob_storage)
    worker.register_events(dispatcher)

    origin_port, proxy_port = get_available_network_port(), get_available_network_port()
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": f"http://127.0.0.1:{origin_port}/"}]}),
        http_client=httpx.AsyncClient(),
        name="api",
        dispatcher=dispatcher,
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    servers = [await _serve(origin, origin_port, shutdown), await _serve(kernel, proxy_port, shutdown)]

    try:
        rejected = await _raw(proxy_port, AMBIGUOUS)
        await worker.wait_until_empty()
        assert origin.requests == []
        assert len(await sql_storage.get_transaction_list(username="anonymous")) == 0

        # control: the same setup does forward and record a valid request
        accepted = await _raw(proxy_port, VALID)
        await worker.wait_until_empty()
        assert origin.requests == ["GET"]
        assert len(await sql_storage.get_transaction_list(username="anonymous")) == 1
    finally:
        shutdown.set()
        await asyncio.gather(*servers)

    assert rejected.startswith(b"HTTP/1.1 400")
    assert accepted.startswith(b"HTTP/1.1 200")
