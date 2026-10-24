"""A failing cache storage never breaks the response nor counts against the upstream (#1272)."""

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://origin.test/item"
BODY = b"0123" * 4


class FailingBlobStorage(MemoryBlobStorage):
    """A blob storage whose operations raise once switched on."""

    def __init__(self):
        super().__init__()
        self.failing: set[str] = set()

    def fail(self, *operations: str) -> None:
        self.failing = set(operations)

    def _check(self, operation: str) -> None:
        if operation in self.failing:
            raise ConnectionError("blob storage down")

    async def put(self, *args, **kwargs):
        self._check("put")
        return await super().put(*args, **kwargs)

    async def get(self, *args, **kwargs):
        self._check("get")
        return await super().get(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        self._check("delete")
        return await super().delete(*args, **kwargs)


class Origin(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"cache-control": "max-age=3600"}, content=BODY)


def make_client(blobs: FailingBlobStorage) -> httpx.AsyncClient:
    async def name_endpoint(request: httpx.Request) -> None:
        request.extensions["harp"] = {"endpoint": "api"}

    transport = AsyncCacheTransport(
        next_transport=Origin(),
        storage=AsyncStorage(blobs),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
    )
    return httpx.AsyncClient(transport=transport, event_hooks={"request": [name_endpoint]})


async def test_failing_put_still_sends_the_whole_body(caplog):
    blobs = FailingBlobStorage()
    blobs.fail("put")
    async with make_client(blobs) as client:
        response = await client.get(URL)

    assert response.content == BODY
    assert "Failed to store cache entry" in caplog.text


async def test_failing_get_is_a_miss():
    blobs = FailingBlobStorage()
    async with make_client(blobs) as client:
        await client.get(URL)
        blobs.fail("get")
        response = await client.get(URL)

    assert response.content == BODY


async def test_failing_delete_does_not_break_an_invalidating_request(caplog):
    blobs = FailingBlobStorage()
    async with make_client(blobs) as client:
        await client.get(URL)
        blobs.fail("delete")
        response = await client.post(URL)

    assert response.content == BODY
    assert "Failed to remove cache entry" in caplog.text


class RevalidatingOrigin(httpx.AsyncBaseTransport):
    """Serves a body that is stale at once, then answers 304 to its validator."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        headers = {"cache-control": "max-age=0", "etag": '"v1"'}
        if "if-none-match" in request.headers:
            return httpx.Response(304, headers=headers)
        return httpx.Response(200, headers=headers, content=BODY)


async def test_failing_put_while_freshening_on_a_304_serves_the_stored_body(caplog):
    blobs = FailingBlobStorage()
    transport = AsyncCacheTransport(
        next_transport=RevalidatingOrigin(),
        storage=AsyncStorage(blobs),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
    )

    async def name_endpoint(request: httpx.Request) -> None:
        request.extensions["harp"] = {"endpoint": "api"}

    async with httpx.AsyncClient(transport=transport, event_hooks={"request": [name_endpoint]}) as client:
        await client.get(URL)
        blobs.fail("put")
        response = await client.get(URL)

    assert response.content == BODY
    assert "Failed to update cache entry" in caplog.text


@pytest.mark.parametrize("operation", ["put", "get", "delete"])
async def test_failing_storage_never_raises_into_the_client(operation):
    blobs = FailingBlobStorage()
    blobs.fail(operation)
    async with make_client(blobs) as client:
        assert (await client.get(URL)).content == BODY
        assert (await client.get(URL)).content == BODY
        assert (await client.post(URL)).content == BODY
