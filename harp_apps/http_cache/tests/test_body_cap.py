"""The cache streams a response through and stores it once read, unless its body is over the recording cap (#911)."""

import asyncio

import httpx
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://origin.test/item"


class Origin(httpx.AsyncBaseTransport):
    """Serves a cacheable body, in the chunks given, and counts the requests it gets."""

    def __init__(self, *chunks: bytes, released: asyncio.Event | None = None):
        self.chunks = chunks
        self.released = released
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(200, headers={"cache-control": "max-age=3600"}, content=self._body())

    async def _body(self):
        for index, chunk in enumerate(self.chunks):
            if index and self.released:
                await self.released.wait()
            yield chunk


def make_client(origin: Origin, max_recorded_body_size: int | None = None) -> httpx.AsyncClient:
    harp = {"endpoint": "api"}
    if max_recorded_body_size is not None:
        harp["max_recorded_body_size"] = max_recorded_body_size

    async def name_endpoint(request: httpx.Request) -> None:
        request.extensions["harp"] = harp

    transport = AsyncCacheTransport(
        next_transport=origin,
        storage=AsyncStorage(MemoryBlobStorage()),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
    )
    return httpx.AsyncClient(transport=transport, event_hooks={"request": [name_endpoint]})


async def test_body_under_the_cap_is_stored():
    origin = Origin(b"0123", b"4567")
    async with make_client(origin, max_recorded_body_size=8) as client:
        assert (await client.get(URL)).content == b"01234567"
        second = await client.get(URL)

    assert second.content == b"01234567"
    assert origin.calls == 1


async def test_body_over_the_cap_is_sent_whole_and_not_stored():
    origin = Origin(b"0123", b"4567", b"8")
    async with make_client(origin, max_recorded_body_size=8) as client:
        assert (await client.get(URL)).content == b"012345678"
        assert (await client.get(URL)).content == b"012345678"

    assert origin.calls == 2


async def test_cap_defaults_to_one_mebibyte():
    origin = Origin(b"x" * (1024 * 1024), b"x")
    async with make_client(origin) as client:
        await client.get(URL)
        await client.get(URL)

    assert origin.calls == 2


async def test_first_chunk_of_a_cacheable_response_is_not_held_back():
    released = asyncio.Event()
    origin = Origin(b"first", b"second", released=released)
    async with make_client(origin) as client:
        try:
            response = await asyncio.wait_for(client.send(client.build_request("GET", URL), stream=True), timeout=1)
            chunks = response.aiter_raw()
            assert await asyncio.wait_for(anext(chunks), timeout=1) == b"first"
        finally:
            released.set()
        assert b"".join([chunk async for chunk in chunks]) == b"second"


async def test_body_left_unread_is_not_stored():
    origin = Origin(b"0123", b"4567")
    async with make_client(origin) as client:
        response = await client.send(client.build_request("GET", URL), stream=True)
        await response.aclose()
        assert (await client.get(URL)).content == b"01234567"

    assert origin.calls == 2


async def test_closing_an_unread_response_releases_the_upstream():
    closed = asyncio.Event()

    class UpstreamBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"0123"

        async def aclose(self):
            closed.set()

    class ClosableOrigin(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, headers={"cache-control": "max-age=3600"}, stream=UpstreamBody())

    async with make_client(ClosableOrigin()) as client:
        response = await client.send(client.build_request("GET", URL), stream=True)
        await response.aclose()

    assert closed.is_set()
