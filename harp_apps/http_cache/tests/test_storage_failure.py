"""A failing cache storage never breaks the response nor counts against the upstream (#1272)."""

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.http_cache.records import MemoryCacheRecords

URL = "http://origin.test/item"
BODY = b"0123" * 4


class FailingRecords(MemoryCacheRecords):
    """Records whose operations raise once switched on."""

    def __init__(self):
        super().__init__()
        self.failing: set[str] = set()

    def fail(self, *operations: str) -> None:
        self.failing = set(operations)

    def _check(self, operation: str) -> None:
        if operation in self.failing:
            raise ConnectionError("cache records down")

    async def put(self, *args, **kwargs):
        self._check("put")
        return await super().put(*args, **kwargs)

    async def get_variants(self, *args, **kwargs):
        self._check("get")
        return await super().get_variants(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        self._check("get")
        return await super().get_by_id(*args, **kwargs)

    async def delete_key(self, *args, **kwargs):
        self._check("delete")
        return await super().delete_key(*args, **kwargs)


class Origin(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"cache-control": "max-age=3600"}, content=BODY)


def make_client(records: FailingRecords) -> httpx.AsyncClient:
    async def name_endpoint(request: httpx.Request) -> None:
        request.extensions["harp"] = {"endpoint": "api"}

    transport = AsyncCacheTransport(
        next_transport=Origin(),
        storage=AsyncStorage(records),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
    )
    return httpx.AsyncClient(transport=transport, event_hooks={"request": [name_endpoint]})


async def test_failing_put_still_sends_the_whole_body(caplog):
    records = FailingRecords()
    records.fail("put")
    async with make_client(records) as client:
        response = await client.get(URL)

    assert response.content == BODY
    assert "Failed to store cache entry" in caplog.text


async def test_failing_get_is_a_miss():
    records = FailingRecords()
    async with make_client(records) as client:
        await client.get(URL)
        records.fail("get")
        response = await client.get(URL)

    assert response.content == BODY


async def test_failing_delete_does_not_break_an_invalidating_request(caplog):
    records = FailingRecords()
    async with make_client(records) as client:
        await client.get(URL)
        records.fail("delete")
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
    records = FailingRecords()
    transport = AsyncCacheTransport(
        next_transport=RevalidatingOrigin(),
        storage=AsyncStorage(records),
        policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
    )

    async def name_endpoint(request: httpx.Request) -> None:
        request.extensions["harp"] = {"endpoint": "api"}

    async with httpx.AsyncClient(transport=transport, event_hooks={"request": [name_endpoint]}) as client:
        await client.get(URL)
        records.fail("put")
        response = await client.get(URL)

    assert response.content == BODY
    assert "Failed to update cache entry" in caplog.text


@pytest.mark.parametrize("operation", ["put", "get", "delete"])
async def test_failing_storage_never_raises_into_the_client(operation):
    records = FailingRecords()
    records.fail(operation)
    async with make_client(records) as client:
        assert (await client.get(URL)).content == BODY
        assert (await client.get(URL)).content == BODY
        assert (await client.post(URL)).content == BODY
