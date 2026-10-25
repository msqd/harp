"""A cache key holds several ``Vary`` variants, at most ``MAX_VARIANTS_PER_KEY`` (#1138)."""

import asyncio
from dataclasses import replace

import httpx
import pytest
import respx
import yaml
from hishel import CacheOptions, Headers, Request, Response, SpecificationPolicy
from hishel._core.models import AnyIterable

from harp_apps.http_cache.storages import MAX_VARIANTS_PER_KEY, AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS, store_entry
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.models.blobs import cache_meta_references
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://origin.test/resource"
KEY = "key"


def _request(accept: str) -> Request:
    return Request(method="GET", url=URL, headers=Headers({"accept": accept}))


def _response(accept: str, vary: str = "Accept") -> Response:
    return Response(
        status_code=200,
        headers=Headers({"cache-control": "max-age=300", "vary": vary, "content-type": "text/plain"}),
        stream=AnyIterable(f"body for {accept}".encode()),
        metadata={},
    )


async def store_variant(storage: AsyncStorage, accept: str):
    return await store_entry(storage, _request(accept), _response(accept), KEY)


async def accepts(storage: AsyncStorage) -> list[str]:
    return [entry.request.headers["accept"] for entry in await storage.get_entries(KEY)]


@pytest.fixture
def blobs():
    return MemoryBlobStorage()


@pytest.fixture
def storage(blobs):
    return AsyncStorage(blobs)


def test_a_key_holds_at_most_eight_variants():
    assert MAX_VARIANTS_PER_KEY == 8


@pytest.mark.asyncio
class TestVariants:
    async def test_variants_of_a_key_coexist(self, storage):
        await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")

        assert await accepts(storage) == ["text/html", "application/json"]

    async def test_storing_a_variant_again_replaces_it(self, storage):
        await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")
        await store_variant(storage, "text/html")

        assert await accepts(storage) == ["application/json", "text/html"]

    async def test_the_ninth_variant_evicts_the_oldest(self, storage):
        wanted = [f"type/{n}" for n in range(MAX_VARIANTS_PER_KEY + 1)]
        for accept in wanted:
            await store_variant(storage, accept)

        assert await accepts(storage) == wanted[1:]

    async def test_variants_of_other_keys_are_not_counted(self, storage):
        for n in range(MAX_VARIANTS_PER_KEY):
            await store_entry(storage, _request(f"type/{n}"), _response("x"), f"other-{n}")
        await store_variant(storage, "text/html")

        assert await accepts(storage) == ["text/html"]

    async def test_a_blob_written_before_variants_is_one_variant(self, storage, blobs):
        """Entries stored by earlier versions hold a single entry at the top of the blob."""
        await store_variant(storage, "text/html")
        blob = await blobs.get(KEY)
        (entry,) = yaml.safe_load(blob.data)["variants"]
        await blobs.force_put(replace(blob, data=yaml.safe_dump(entry).encode()))

        assert await accepts(AsyncStorage(blobs)) == ["text/html"]

    async def test_every_variant_is_referenced_for_the_janitor(self, storage, blobs):
        await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")

        references = cache_meta_references((await blobs.get(KEY)).data)

        # two request headers and two bodies, and the response headers they share
        assert len(references) == 5


@pytest.mark.asyncio
class TestOneVariantAtATime:
    async def test_update_entry_touches_only_its_variant(self, storage):
        html = await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")

        await storage.update_entry(
            html.id,
            lambda e: replace(e, response=replace(e.response, headers=Headers({**e.response.headers, "etag": '"x"'}))),
        )

        etags = {e.request.headers["accept"]: e.response.headers.get("etag") for e in await storage.get_entries(KEY)}
        assert etags == {"text/html": '"x"', "application/json": None}

    async def test_remove_entry_drops_only_its_variant(self, storage):
        html = await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")

        await storage.remove_entry(html.id)

        assert await accepts(storage) == ["application/json"]

    async def test_removing_the_last_variant_deletes_the_blob(self, storage, blobs):
        html = await store_variant(storage, "text/html")

        await storage.remove_entry(html.id)

        assert await blobs.get(KEY) is None

    async def test_concurrent_stores_keep_every_variant(self, storage):
        await asyncio.gather(*(store_variant(storage, f"type/{n}") for n in range(5)))

        assert sorted(await accepts(storage)) == [f"type/{n}" for n in range(5)]


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now

    def monotonic(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("harp_apps.http_cache.storages.time", clock)
    monkeypatch.setattr("harp_apps.http_cache.adapters.time", clock)
    return clock


@pytest.mark.asyncio
class TestExpiry:
    async def test_the_sweep_deletes_a_blob_whose_variants_all_expired(self, blobs, clock):
        storage = AsyncStorage(blobs, ttl=100, check_ttl_every=10)
        await store_variant(storage, "text/html")
        await store_variant(storage, "application/json")
        clock.now += 101
        await store_entry(storage, _request("x"), _response("x"), "other")
        await storage.wait_for_sweep()

        assert [blob.id async for blob in blobs.iter_blobs("cache/meta")] == ["other"]

    async def test_the_sweep_keeps_the_variants_still_live(self, blobs, clock):
        storage = AsyncStorage(blobs, ttl=100, check_ttl_every=10)
        await store_variant(storage, "text/html")
        clock.now += 60
        await store_variant(storage, "application/json")
        clock.now += 60
        await storage.get_entries("elsewhere")
        await storage.wait_for_sweep()

        assert len(yaml.safe_load((await blobs.get(KEY)).data)["variants"]) == 1
        assert await accepts(storage) == ["application/json"]

    async def test_an_expired_variant_is_not_served_nor_counted(self, blobs, clock):
        storage = AsyncStorage(blobs, ttl=100, check_ttl_every=10_000)
        await store_variant(storage, "text/html")
        clock.now += 101
        for n in range(MAX_VARIANTS_PER_KEY):
            await store_variant(storage, f"type/{n}")

        assert await accepts(storage) == [f"type/{n}" for n in range(MAX_VARIANTS_PER_KEY)]


@pytest.mark.asyncio
class TestThroughTheTransport:
    @respx.mock
    async def test_alternating_accept_values_cost_one_origin_request_each(self, storage):
        def origin(request: httpx.Request) -> httpx.Response:
            accept = request.headers["accept"]
            return httpx.Response(
                200,
                content=f"body for {accept}".encode(),
                headers={"cache-control": "max-age=300", "vary": "Accept", "content-type": "text/plain"},
            )

        route = respx.get(URL).mock(side_effect=origin)
        transport = AsyncCacheTransport(
            next_transport=httpx.AsyncHTTPTransport(),
            storage=storage,
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"])),
        )
        async with httpx.AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS) as client:
            for _ in range(3):
                for accept in ("text/html", "application/json", "text/plain"):
                    response = await client.get(URL, headers={"accept": accept})
                    assert response.content == f"body for {accept}".encode()

        assert route.call_count == 3
