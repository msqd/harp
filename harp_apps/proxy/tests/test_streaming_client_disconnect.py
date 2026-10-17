"""A client leaving mid-body stops the proxy reading the upstream, through a real ASGI server (#911)."""

import asyncio

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy
from hypercorn.asyncio import serve
from hypercorn.config import Config

from harp.asgi import ASGIKernel
from harp.controllers import DefaultControllerResolver
from harp.utils.network import get_available_network_port, wait_for_port
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.constants import CLIENT_DISCONNECTED
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

BODY_SIZE = 256 * 1024 * 1024
CHUNK = b"x" * 65536
CAP = 1024 * 1024


class SlowOrigin:
    """Serves a large body slowly, and stops as soon as the proxy hangs up."""

    def __init__(self):
        self.sent = 0
        self.hung_up = asyncio.Event()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while (await receive())["type"] != "lifespan.shutdown":
                await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
            return

        async def watch():
            while (await receive())["type"] != "http.disconnect":
                pass
            self.hung_up.set()

        watcher = asyncio.create_task(watch())
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-length", str(BODY_SIZE).encode()), (b"cache-control", b"max-age=3600")],
            }
        )
        while self.sent < BODY_SIZE and not self.hung_up.is_set():
            await send({"type": "http.response.body", "body": CHUNK, "more_body": True})
            self.sent += len(CHUNK)
            await asyncio.sleep(0.001)
        watcher.cancel()


class Recorder:
    def __init__(self):
        self.ended = asyncio.Event()
        self.transaction = None
        self.response = None

    async def adispatch(self, event_id, event=None):
        if event_id == EVENT_TRANSACTION_MESSAGE and event.message.kind == "response":
            self.response = event.message
        if event_id == EVENT_TRANSACTION_ENDED:
            self.transaction = event.transaction
            self.ended.set()
        return event


def _plain_client():
    return httpx.AsyncClient()


def _cached_client():
    return httpx.AsyncClient(
        transport=AsyncCacheTransport(
            next_transport=httpx.AsyncHTTPTransport(),
            storage=AsyncStorage(MemoryBlobStorage()),
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )
    )


async def _serve(app, port, shutdown):
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    server = asyncio.ensure_future(serve(app, config=config, shutdown_trigger=shutdown.wait))
    await asyncio.to_thread(wait_for_port, port, "127.0.0.1")
    return server


@pytest.mark.parametrize("make_client", [_plain_client, _cached_client], ids=["no-cache", "with-cache"])
async def test_client_leaving_mid_body_stops_the_upstream_read(make_client):
    origin, recorder, shutdown = SlowOrigin(), Recorder(), asyncio.Event()
    origin_port, proxy_port = get_available_network_port(), get_available_network_port()
    controller = HttpProxyController(
        Remote.from_settings_dict({"endpoints": [{"url": f"http://127.0.0.1:{origin_port}/"}]}),
        http_client=make_client(),
        name="api",
        dispatcher=recorder,
        max_recorded_body_size=CAP,
    )
    kernel = ASGIKernel(resolver=DefaultControllerResolver(default_controller=controller))
    await ASGICommunicator(kernel).asgi_lifespan_startup()
    servers = [await _serve(origin, origin_port, shutdown), await _serve(kernel, proxy_port, shutdown)]

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"http://127.0.0.1:{proxy_port}/") as response:
                received = 0
                async for chunk in response.aiter_raw():
                    received += len(chunk)
                    if received > 2 * CAP:
                        break

        await asyncio.wait_for(origin.hung_up.wait(), timeout=10)
        await asyncio.wait_for(recorder.ended.wait(), timeout=10)
    finally:
        shutdown.set()
        await asyncio.gather(*servers)

    assert origin.sent < BODY_SIZE // 4
    assert CLIENT_DISCONNECTED in recorder.transaction.markers
    assert len(await recorder.response.aread()) == CAP
