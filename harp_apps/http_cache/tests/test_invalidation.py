"""RFC 9111 §4.4: a successful unsafe request invalidates what the cache holds for the resource."""

import asyncio

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.http_cache.records import MemoryCacheRecords

HOST = "http://origin.test"


class Origin(httpx.AsyncBaseTransport):
    """Serves a body that changes on every write; GET responses are cacheable."""

    def __init__(self, write_status: int = 200, write_headers: dict[str, str] | None = None):
        self.version = 1
        self.requests: list[tuple[str, str]] = []
        self.write_status = write_status
        self.write_headers = write_headers or {}

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.method in ("GET", "HEAD"):
            return httpx.Response(
                200, headers={"cache-control": "max-age=3600"}, content=f"v{self.version}:{request.url.path}".encode()
            )
        if self.write_status < 400:
            self.version += 1
        return httpx.Response(self.write_status, headers=self.write_headers)

    def gets(self, path: str) -> int:
        return self.requests.count(("GET", path))


def make_client(origin: Origin, mock_storage) -> httpx.AsyncClient:
    policy = SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"]))
    transport = AsyncCacheTransport(next_transport=origin, storage=mock_storage, policy=policy)
    return httpx.AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS)


@pytest.mark.asyncio
class TestUnsafeMethodInvalidatesTarget:
    @pytest.mark.parametrize("method", ["PUT", "POST", "PATCH", "DELETE"])
    async def test_next_get_reaches_origin(self, mock_storage, method):
        origin = Origin()
        async with make_client(origin, mock_storage) as client:
            assert (await client.get(f"{HOST}/item")).text == "v1:/item"
            assert (await client.get(f"{HOST}/item")).text == "v1:/item"
            assert origin.gets("/item") == 1

            await client.request(method, f"{HOST}/item")

            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
            assert origin.gets("/item") == 2

    async def test_redirect_response_invalidates(self, mock_storage):
        origin = Origin(write_status=303)
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item")
            await client.post(f"{HOST}/item")
            await client.get(f"{HOST}/item")
        assert origin.gets("/item") == 2

    @pytest.mark.parametrize("status", [400, 404, 500, 503])
    async def test_error_response_invalidates_nothing(self, mock_storage, status):
        origin = Origin(write_status=status, write_headers={"location": "/other"})
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
            await client.put(f"{HOST}/item")
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
        assert origin.gets("/item") == 1
        assert origin.gets("/other") == 1

    async def test_other_resources_are_untouched(self, mock_storage):
        origin = Origin()
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/unrelated")
            await client.put(f"{HOST}/item")
            await client.get(f"{HOST}/unrelated")
        assert origin.gets("/unrelated") == 1

    async def test_query_string_is_part_of_the_target(self, mock_storage):
        origin = Origin()
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item?a=1")
            await client.put(f"{HOST}/item?a=1")
            await client.get(f"{HOST}/item?a=1")
        assert origin.gets("/item") == 2

    async def test_safe_methods_invalidate_nothing(self, mock_storage):
        origin = Origin()
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item")
            await client.options(f"{HOST}/item")
            await client.head(f"{HOST}/item")
            await client.get(f"{HOST}/item")
        assert origin.gets("/item") == 1

    async def test_no_store_request_still_invalidates(self, mock_storage):
        origin = Origin()
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/item")
            await client.put(f"{HOST}/item", headers={"cache-control": "no-store"})
            await client.get(f"{HOST}/item")
        assert origin.gets("/item") == 2


@pytest.mark.asyncio
class TestLocationHeadersInvalidate:
    @pytest.mark.parametrize("header", ["Location", "Content-Location"])
    @pytest.mark.parametrize("value", ["/other", f"{HOST}/other"], ids=["relative", "absolute"])
    async def test_same_host_uri_is_invalidated(self, mock_storage, header, value):
        origin = Origin(write_status=201, write_headers={header: value})
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/other")
            await client.post(f"{HOST}/items")
            assert (await client.get(f"{HOST}/other")).text == "v2:/other"
        assert origin.gets("/other") == 2

    @pytest.mark.parametrize("header", ["Location", "Content-Location"])
    async def test_other_host_uri_is_not_invalidated(self, mock_storage, header):
        origin = Origin(write_status=201, write_headers={header: "http://elsewhere.test/other"})
        async with make_client(origin, mock_storage) as client:
            await client.get(f"{HOST}/other")
            await client.post(f"{HOST}/items")
            await client.get(f"{HOST}/other")
        assert origin.gets("/other") == 1

    async def test_both_headers_and_target_are_invalidated(self, mock_storage):
        origin = Origin(write_status=201, write_headers={"Location": "/a", "Content-Location": "/b"})
        async with make_client(origin, mock_storage) as client:
            for path in ("/items", "/a", "/b"):
                await client.get(f"{HOST}{path}")
            await client.post(f"{HOST}/items")
            for path in ("/items", "/a", "/b"):
                await client.get(f"{HOST}{path}")
        assert [origin.gets(p) for p in ("/items", "/a", "/b")] == [2, 2, 2]

    async def test_unparsable_location_does_not_break_the_response(self, mock_storage):
        origin = Origin(write_status=201, write_headers={"Location": "http://[bad"})
        async with make_client(origin, mock_storage) as client:
            response = await client.post(f"{HOST}/items")
        assert response.status_code == 201


@pytest.mark.asyncio
async def test_invalidates_entries_held_by_the_real_storage():
    origin = Origin()
    async with make_client(origin, AsyncStorage(MemoryCacheRecords())) as client:
        await client.get(f"{HOST}/item")
        await client.get(f"{HOST}/item")
        await client.put(f"{HOST}/item")
        assert (await client.get(f"{HOST}/item")).text == "v2:/item"
    assert origin.gets("/item") == 2


class SlowOrigin(Origin):
    """Reads the resource when the GET arrives, and sends it slowly: a write can land while it is on its way."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slow_paths: set[str] = {"/item"}
        self.release = asyncio.Event()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method != "GET" or request.url.path not in self.slow_paths:
            return await super().handle_async_request(request)
        self.requests.append((request.method, request.url.path))
        body = f"v{self.version}:{request.url.path}".encode()

        release = self.release

        class Slowly(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield body[:2]
                await release.wait()
                yield body[2:]

        return httpx.Response(200, headers={"cache-control": "max-age=3600"}, stream=Slowly())


async def _until(condition) -> None:
    for _ in range(200):
        if condition():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("the condition never came true")


@pytest.mark.asyncio
class TestGetInFlightDuringInvalidation:
    async def test_old_body_is_not_stored_after_a_write(self):
        origin = SlowOrigin()
        async with make_client(origin, AsyncStorage(MemoryCacheRecords())) as client:
            slow_get = asyncio.create_task(client.get(f"{HOST}/item"))
            await _until(lambda: origin.gets("/item") == 1)

            await client.post(f"{HOST}/item")
            origin.release.set()
            assert (await slow_get).text == "v1:/item"  # the GET that started before the write is answered as it was

            origin.slow_paths.clear()
            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
        assert origin.gets("/item") == 2

    async def test_get_not_overlapping_a_write_is_stored(self):
        origin = SlowOrigin()
        origin.release.set()
        async with make_client(origin, AsyncStorage(MemoryCacheRecords())) as client:
            await client.post(f"{HOST}/item")
            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
        assert origin.gets("/item") == 1

    async def test_get_in_flight_for_another_resource_is_stored(self):
        origin = SlowOrigin()
        origin.slow_paths = {"/other"}
        async with make_client(origin, AsyncStorage(MemoryCacheRecords())) as client:
            slow_get = asyncio.create_task(client.get(f"{HOST}/other"))
            await _until(lambda: origin.gets("/other") == 1)

            await client.post(f"{HOST}/item")
            origin.release.set()
            await slow_get

            await client.get(f"{HOST}/other")
        assert origin.gets("/other") == 1
