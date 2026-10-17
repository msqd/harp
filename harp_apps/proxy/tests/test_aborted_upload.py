"""A client aborting its upload is not forwarded upstream as a complete request (#1217), through real ASGI servers."""

import asyncio
from functools import partial
from unittest.mock import AsyncMock, MagicMock

import httpx
from hypercorn.asyncio import serve
from hypercorn.config import Config
from whistle import AsyncEventDispatcher

from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_TRANSACTION_ENDED
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.constants import CLIENT_DISCONNECTED, TRUNCATED_REQUEST_BODY
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage
from harp_apps.storage.worker import StorageAsyncWorkerQueue

DECLARED = 10_000_000
SENT = 1_000_000


class Origin:
    def __init__(self):
        self.requests = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while (await receive())["type"] != "lifespan.shutdown":
                await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
            return
        self.requests.append(scope["method"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})


class Recorder:
    def __init__(self):
        self.ended = asyncio.Event()
        self.transaction = None

    async def adispatch(self, event_id, event=None):
        if event_id == EVENT_TRANSACTION_ENDED:
            self.transaction = event.transaction
            self.ended.set()
        return event


async def _serve(app, port, shutdown):
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    server = asyncio.ensure_future(serve(app, config=config, shutdown_trigger=shutdown.wait))
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    return server


async def test_aborted_upload_is_not_forwarded():
    origin, recorder, shutdown = Origin(), Recorder(), asyncio.Event()
    origin_port, proxy_port = get_available_network_port(), get_available_network_port()
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": f"http://127.0.0.1:{origin_port}/"}]}),
        http_client=httpx.AsyncClient(),
        name="api",
        dispatcher=recorder,
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    servers = [await _serve(origin, origin_port, shutdown), await _serve(kernel, proxy_port, shutdown)]

    try:
        _, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
        writer.write(
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Type: application/octet-stream\r\n"
            + f"Content-Length: {DECLARED}\r\n\r\n".encode()
            + b"x" * SENT
        )
        await writer.drain()
        await asyncio.sleep(0.3)
        writer.close()

        await asyncio.wait_for(recorder.ended.wait(), timeout=10)
        await asyncio.sleep(0.3)
    finally:
        shutdown.set()
        await asyncio.gather(*servers)

    assert origin.requests == []
    assert CLIENT_DISCONNECTED in recorder.transaction.markers


async def test_aborted_upload_is_recorded_with_storage_enabled(caplog):
    origin, recorder, shutdown = Origin(), Recorder(), asyncio.Event()
    dispatcher = AsyncEventDispatcher()
    dispatcher.add_listener(EVENT_TRANSACTION_ENDED, partial(recorder.adispatch, EVENT_TRANSACTION_ENDED))
    worker = StorageAsyncWorkerQueue(MagicMock(), AsyncMock(), MemoryBlobStorage())
    worker.register_events(dispatcher)
    pushed = []

    async def push(item, **kwargs):
        pushed.append(item)

    worker.push = push

    origin_port, proxy_port = get_available_network_port(), get_available_network_port()
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": f"http://127.0.0.1:{origin_port}/"}]}),
        http_client=httpx.AsyncClient(),
        name="api",
        dispatcher=dispatcher,
        max_recorded_body_size=1000,
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    servers = [await _serve(origin, origin_port, shutdown), await _serve(kernel, proxy_port, shutdown)]

    try:
        _, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
        writer.write(
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Type: application/octet-stream\r\n"
            + f"Content-Length: {DECLARED}\r\n\r\n".encode()
            + b"x" * SENT
        )
        await writer.drain()
        await asyncio.sleep(0.3)
        writer.close()

        await asyncio.wait_for(recorder.ended.wait(), timeout=10)
        await asyncio.sleep(0.3)
    finally:
        shutdown.set()
        await asyncio.gather(*servers)

    assert origin.requests == []
    assert CLIENT_DISCONNECTED in recorder.transaction.markers
    assert TRUNCATED_REQUEST_BODY in recorder.transaction.markers
    assert "ClientDisconnected" not in caplog.text
    blobs = [p.args[0].data for p in pushed if isinstance(p, partial) and p.args and hasattr(p.args[0], "data")]
    assert [len(blob) for blob in blobs if blob.startswith(b"x")] == [1000]
