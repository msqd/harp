"""Invalidating a key, an endpoint or everything through the storage, on every records backend (ADR-0014)."""

import asyncio

import httpx
import pytest

from harp_apps.http_cache.records import BanMode
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests.test_invalidation import HOST, SlowOrigin, _until, make_client

ENDPOINT = "test-endpoint"


class ValidatedOrigin(httpx.AsyncBaseTransport):
    """Serves a body with an ``ETag`` that changes when ``version`` does, and ``304`` to a matching validator."""

    def __init__(self):
        self.version = 1
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        etag = f'"v{self.version}"'
        if request.method == "GET" and request.headers.get("if-none-match") == etag:
            return httpx.Response(304, headers={"etag": etag, "cache-control": "max-age=3600"})
        if request.method == "GET":
            headers = {"etag": etag, "cache-control": "max-age=3600"}
            return httpx.Response(200, headers=headers, content=f"v{self.version}:{request.url.path}".encode())
        self.version += 1
        return httpx.Response(200)

    @property
    def conditional(self) -> int:
        return sum(1 for request in self.requests if "if-none-match" in request.headers)


@pytest.fixture
def storage(records):
    return AsyncStorage(records)


@pytest.mark.asyncio
class TestSoftBan:
    async def test_entries_are_revalidated_and_the_validated_body_is_kept(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            response = await client.get(f"{HOST}/item")

        assert response.text == "v1:/item"
        assert len(origin.requests) == 2
        assert origin.conditional == 1

    async def test_the_entry_is_fresh_again_once_revalidated(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)
            await client.get(f"{HOST}/item")

            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/item")

        assert len(origin.requests) == 2

    async def test_a_changed_resource_is_fetched_again(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            origin.version = 2
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
            assert (await client.get(f"{HOST}/item")).text == "v2:/item"

        assert len(origin.requests) == 2

    async def test_an_exact_key_is_revalidated_too(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
            await storage.invalidate(f"http://{ENDPOINT}/item", mode=BanMode.SOFT)

            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")

        assert origin.conditional == 1


@pytest.mark.asyncio
class TestHardBan:
    async def test_an_endpoint_is_fetched_again(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
            origin.version = 2
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.HARD)

            assert (await client.get(f"{HOST}/item")).text == "v2:/item"
            assert (await client.get(f"{HOST}/other")).text == "v2:/other"

        assert origin.conditional == 0

    async def test_another_endpoint_is_untouched(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item", extensions={"harp": {"endpoint": "elsewhere"}})
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.HARD)
            await client.get(f"{HOST}/item", extensions={"harp": {"endpoint": "elsewhere"}})

        assert len(origin.requests) == 1

    async def test_everything_is_fetched_again(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/item", extensions={"harp": {"endpoint": "elsewhere"}})
            await storage.invalidate_all(mode=BanMode.HARD)

            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/item", extensions={"harp": {"endpoint": "elsewhere"}})

        assert len(origin.requests) == 4

    async def test_a_key_is_fetched_again(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await storage.invalidate(f"http://{ENDPOINT}/item", mode=BanMode.HARD)

            await client.get(f"{HOST}/item")

        assert len(origin.requests) == 2


@pytest.mark.asyncio
class TestUnsafeMethod:
    async def test_it_appends_one_ban_covering_the_target_only(self, records, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/other")
            assert await records.counter() == 0

            await client.put(f"{HOST}/item")

            assert await records.counter() == 1
            assert await records.get_variants(f"http://{ENDPOINT}/item") == []
            assert len(await records.get_variants(f"http://{ENDPOINT}/other")) == 1


@pytest.mark.asyncio
class TestFetchInFlightDuringInvalidation:
    """Two instances of HARP share the records: the invalidation of one must keep the fetch of the other out."""

    async def test_a_fetch_started_before_an_endpoint_ban_is_not_stored(self, records):
        origin = SlowOrigin()
        async with make_client(origin, AsyncStorage(records)) as fetcher:
            slow_get = asyncio.create_task(fetcher.get(f"{HOST}/item"))
            await _until(lambda: origin.gets("/item") == 1)

            await AsyncStorage(records).invalidate_endpoint(ENDPOINT, mode=BanMode.HARD)
            origin.release.set()
            await slow_get

            origin.slow_paths.clear()
            await fetcher.get(f"{HOST}/item")

        assert origin.gets("/item") == 2

    async def test_a_fetch_started_before_a_soft_ban_is_not_stored_either(self, records):
        origin = SlowOrigin()
        async with make_client(origin, AsyncStorage(records)) as fetcher:
            slow_get = asyncio.create_task(fetcher.get(f"{HOST}/item"))
            await _until(lambda: origin.gets("/item") == 1)

            await AsyncStorage(records).invalidate_all(mode=BanMode.SOFT)
            origin.release.set()
            await slow_get

            origin.slow_paths.clear()
            await fetcher.get(f"{HOST}/item")

        assert origin.gets("/item") == 2

    async def test_a_fetch_started_before_a_write_on_another_instance_is_not_stored(self, records):
        origin = SlowOrigin()
        async with (
            make_client(origin, AsyncStorage(records)) as fetcher,
            make_client(origin, AsyncStorage(records)) as writer,
        ):
            slow_get = asyncio.create_task(fetcher.get(f"{HOST}/item"))
            await _until(lambda: origin.gets("/item") == 1)

            await writer.post(f"{HOST}/item")
            origin.release.set()
            await slow_get

            origin.slow_paths.clear()
            assert (await fetcher.get(f"{HOST}/item")).text == "v2:/item"

    async def test_a_fetch_started_after_a_ban_is_stored(self, records):
        origin = SlowOrigin()
        origin.release.set()
        async with make_client(origin, AsyncStorage(records)) as client:
            await AsyncStorage(records).invalidate_endpoint(ENDPOINT, mode=BanMode.HARD)

            await client.get(f"{HOST}/item")
            await client.get(f"{HOST}/item")

        assert origin.gets("/item") == 1
