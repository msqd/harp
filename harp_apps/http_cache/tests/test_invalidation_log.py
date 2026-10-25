"""Invalidating a key, an endpoint or everything through the storage, on every records backend (ADR-0014)."""

import asyncio
import time
from email.utils import formatdate

import httpx
import pytest
from hishel import CacheOptions, SpecificationPolicy

from harp_apps.http_cache.records import BanMode
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport
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


class FreshnessOrigin(ValidatedOrigin):
    """Like :class:`ValidatedOrigin`, with the freshness headers of the test's choosing."""

    def __init__(self, freshness):
        """``freshness`` is a dict of headers, or a function making one (an ``Expires`` moves with time)."""
        super().__init__()
        self.freshness = freshness

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await super().handle_async_request(request)
        for name in ("cache-control", "expires"):
            response.headers.pop(name, None)
        response.headers.update(self.freshness() if callable(self.freshness) else self.freshness)
        return response


def _expires_in_an_hour() -> dict[str, str]:
    return {"expires": formatdate(time.time() + 3600, usegmt=True)}


def _client(origin, storage, *, allow_stale=False) -> httpx.AsyncClient:
    policy = SpecificationPolicy(
        cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=allow_stale)
    )
    transport = AsyncCacheTransport(next_transport=origin, storage=storage, policy=policy)
    return httpx.AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS)


@pytest.mark.asyncio
class TestSoftBanWhateverMakesTheEntryFresh:
    """The entry is shown to hishel in a form it cannot read as fresh, nor as stale but allowed."""

    @pytest.mark.parametrize(
        "freshness",
        [
            pytest.param(_expires_in_an_hour, id="expires"),
            pytest.param({"cache-control": "max-age=2147483648"}, id="huge-max-age"),
            pytest.param({"cache-control": "s-maxage=3600"}, id="s-maxage"),
            pytest.param({"cache-control": "max-age=3600, stale-while-revalidate=600"}, id="stale-while-revalidate"),
        ],
    )
    @pytest.mark.parametrize("allow_stale", [False, True])
    async def test_it_is_revalidated_before_being_served(self, storage, freshness, allow_stale):
        origin = FreshnessOrigin(freshness)
        async with _client(origin, storage, allow_stale=allow_stale) as client:
            await client.get(f"{HOST}/item")
            origin.version = 2
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            response = await client.get(f"{HOST}/item")

        assert response.text == "v2:/item"
        assert len(origin.requests) == 2

    @pytest.mark.parametrize("allow_stale", [False, True])
    async def test_a_304_restores_what_the_origin_said_and_the_entry_is_fresh_again(self, storage, allow_stale):
        origin = FreshnessOrigin(_expires_in_an_hour)
        async with _client(origin, storage, allow_stale=allow_stale) as client:
            await client.get(f"{HOST}/item")
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            revalidated = await client.get(f"{HOST}/item")
            hit = await client.get(f"{HOST}/item")

        assert len(origin.requests) == 2
        for response in (revalidated, hit):
            assert "expires" in response.headers
            assert "cache-control" not in response.headers
            assert not [name for name in response.headers if name.startswith("x-harp")]

    async def test_the_cache_control_of_the_origin_comes_back(self, storage):
        origin = FreshnessOrigin({"cache-control": "max-age=3600, public"})
        async with _client(origin, storage) as client:
            await client.get(f"{HOST}/item")
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            revalidated = await client.get(f"{HOST}/item")
            hit = await client.get(f"{HOST}/item")

        assert len(origin.requests) == 2
        assert revalidated.headers["cache-control"] == hit.headers["cache-control"] == "max-age=3600, public"


@pytest.mark.asyncio
class TestEndpointNames:
    async def test_an_endpoint_with_capitals_is_invalidated(self, storage):
        origin = ValidatedOrigin()
        extensions = {"harp": {"endpoint": "MyAPI"}}
        async with make_client(origin, storage) as client:
            await client.get(f"{HOST}/item", extensions=extensions)
            origin.version = 2

            await storage.invalidate_endpoint("MyAPI", mode=BanMode.HARD)

            assert (await client.get(f"{HOST}/item", extensions=extensions)).text == "v2:/item"

    async def test_an_https_endpoint_is_invalidated(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get("https://origin.test/item")
            origin.version = 2

            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.HARD)

            assert (await client.get("https://origin.test/item")).text == "v2:/item"

    async def test_an_https_endpoint_is_revalidated_by_a_soft_ban(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await client.get("https://origin.test/item")
            await storage.invalidate_endpoint(ENDPOINT, mode=BanMode.SOFT)

            await client.get("https://origin.test/item")

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
