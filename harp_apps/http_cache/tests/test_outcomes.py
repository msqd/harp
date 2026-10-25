"""What the cache did for each response, reported to the proxy (#404).

The transport adds a ``harp_cache`` extension to every response that went through the cache: the outcome, the cache key,
the variant, the invalidation number the response is valid as of, and the freshness left. The proxy records it on the
transaction.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp.models.transactions import CacheOutcome
from harp_apps.http_cache.adapters import variant_of
from harp_apps.http_cache.records import BanMode, MemoryCacheRecords
from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport

URL = "http://example.com/resource"
KEY = "http://test-endpoint/resource"


def _http_date(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).strftime("%a, %d %b %Y %H:%M:%S GMT")


@pytest.fixture
def storage():
    return AsyncStorage(MemoryCacheRecords())


def _client(storage, *, allow_stale=False):
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=storage,
        policy=SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=allow_stale)
        ),
    )
    return AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS)


def _origin(headers, *, url=URL, status=200):
    """An origin answering a numbered body, or ``304`` to a request carrying a matching validator."""
    seen = []

    def respond(request):
        seen.append(request)
        if request.headers.get("if-none-match") == headers.get("etag") and "if-none-match" in request.headers:
            return Response(304)
        return Response(status, content=f"body-{len(seen)}".encode(), headers=headers)

    respx.get(url).mock(side_effect=respond)
    return seen


def _cache(response: httpx.Response) -> dict:
    return response.extensions["harp_cache"]


@pytest.mark.asyncio
class TestOutcome:
    @respx.mock
    async def test_first_response_is_a_miss_then_a_hit(self, storage):
        _origin({"cache-control": "max-age=60"})

        async with _client(storage) as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert _cache(first)["outcome"] == CacheOutcome.MISS
        assert _cache(second)["outcome"] == CacheOutcome.HIT

    @respx.mock
    async def test_remaining_freshness(self, storage):
        _origin({"cache-control": "max-age=60"})

        async with _client(storage) as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert 58 <= _cache(first)["ttl"] <= 60
        assert 58 <= _cache(second)["ttl"] <= 60

    @respx.mock
    async def test_a_validated_response_is_revalidated(self, storage):
        _origin({"cache-control": "max-age=0", "etag": '"v1"'})

        async with _client(storage) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert _cache(second)["outcome"] == CacheOutcome.REVALIDATED

    @respx.mock
    async def test_a_revalidation_answered_by_a_new_response_is_a_miss(self, storage):
        seen = _origin({"cache-control": "max-age=0", "etag": '"v1"'})

        def changed(request):
            seen.append(request)
            return Response(200, content=b"new", headers={"cache-control": "max-age=60", "etag": '"v2"'})

        async with _client(storage) as client:
            await client.get(URL)
            respx.get(URL).mock(side_effect=changed)
            second = await client.get(URL)

        assert _cache(second)["outcome"] == CacheOutcome.MISS

    @respx.mock
    async def test_a_stale_response_served_as_it_is(self, storage):
        _origin({"cache-control": "max-age=60", "date": _http_date(timedelta(hours=-1))})

        async with _client(storage, allow_stale=True) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert _cache(second)["outcome"] == CacheOutcome.STALE
        assert _cache(second)["ttl"] == 0

    @respx.mock
    async def test_a_response_the_cache_cannot_store_is_not_cacheable(self, storage):
        _origin({"cache-control": "no-store"})

        async with _client(storage) as client:
            response = await client.get(URL)

        assert _cache(response)["outcome"] == CacheOutcome.UNCACHEABLE
        assert _cache(response)["ttl"] is None

    @respx.mock
    async def test_a_request_forbidding_storage_is_not_cacheable(self, storage):
        _origin({"cache-control": "max-age=60"})

        async with _client(storage) as client:
            response = await client.get(URL, headers={"cache-control": "no-store"})

        assert _cache(response)["outcome"] == CacheOutcome.UNCACHEABLE

    @respx.mock
    async def test_a_method_the_cache_does_not_serve_is_not_cacheable(self, storage):
        respx.post(URL).mock(return_value=Response(200))

        async with _client(storage) as client:
            response = await client.post(URL)

        assert _cache(response)["outcome"] == CacheOutcome.UNCACHEABLE


@pytest.mark.asyncio
class TestWhichEntry:
    @respx.mock
    async def test_key_is_the_cache_key(self, storage):
        _origin({"cache-control": "max-age=60"})

        async with _client(storage) as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert _cache(first)["key"] == KEY
        assert _cache(second)["key"] == KEY

    @respx.mock
    async def test_key_holds_the_hash_of_the_query_never_its_values(self, storage):
        _origin({"cache-control": "max-age=60"}, url=URL + "?token=secret-value")

        async with _client(storage) as client:
            first = await client.get(URL + "?token=secret-value")
            second = await client.get(URL + "?token=secret-value")

        for response in (first, second):
            assert _cache(response)["key"].startswith(KEY + "?")
            assert "secret-value" not in str(_cache(response))

    @respx.mock
    async def test_variant_of_a_response_that_does_not_vary_is_empty(self, storage):
        _origin({"cache-control": "max-age=60"})

        async with _client(storage) as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert _cache(first)["variant"] == ""
        assert _cache(second)["variant"] == ""

    @respx.mock
    async def test_variant_of_a_varying_response(self, storage):
        _origin({"cache-control": "max-age=60", "vary": "accept"})
        variant = variant_of({"accept": "text/plain"})

        async with _client(storage) as client:
            first = await client.get(URL, headers={"accept": "text/plain"})
            second = await client.get(URL, headers={"accept": "text/plain"})

        assert _cache(first)["variant"] == variant
        assert _cache(second)["variant"] == variant

    @respx.mock
    async def test_not_cacheable_has_no_variant(self, storage):
        _origin({"cache-control": "no-store"})

        async with _client(storage) as client:
            response = await client.get(URL)

        assert _cache(response)["variant"] is None


@pytest.mark.asyncio
class TestInvalidationNumber:
    @respx.mock
    async def test_a_response_is_valid_as_of_the_number_read_before_its_fetch(self, storage):
        _origin({"cache-control": "max-age=60"})
        await storage.invalidate(KEY, mode=BanMode.HARD)

        async with _client(storage) as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert _cache(first)["seq"] == 1
        assert _cache(second)["seq"] == 1

    @respx.mock
    async def test_a_revalidation_raises_it_to_the_number_of_its_fetch(self, storage):
        _origin({"cache-control": "max-age=60", "etag": '"v1"'})

        async with _client(storage) as client:
            first = await client.get(URL)
            await storage.invalidate(KEY, mode=BanMode.SOFT)
            second = await client.get(URL)

        assert _cache(first)["seq"] == 0
        assert _cache(second)["outcome"] == CacheOutcome.REVALIDATED
        assert _cache(second)["seq"] == 1
