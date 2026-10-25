"""A response carrying only a validator is kept, and revalidated on every use (#874).

``ETag`` or ``Last-Modified`` without ``Cache-Control`` or ``Expires`` gives the cache nothing to say how long
the response stays fresh, and HARP does not invent it (see ``test_heuristics``). It does not have to throw the
response away either: it keeps it as an entry that is never fresh, so the origin is asked each time with a
conditional request, and a ``304`` saves the body.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from hishel import CacheOptions, SpecificationPolicy
from httpx import AsyncClient, AsyncHTTPTransport, Response

from harp_apps.http_cache.storages import AsyncStorage
from harp_apps.http_cache.tests import ENDPOINT_HOOKS
from harp_apps.http_cache.transports import AsyncCacheTransport
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage

URL = "http://example.com/resource"


def _http_date(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).strftime("%a, %d %b %Y %H:%M:%S GMT")


class _StorageThatCannotUpdate(AsyncStorage):
    async def update_entry(self, id, new_entry):
        return None


def _client(*, allow_heuristics=False, storage_class=AsyncStorage):
    transport = AsyncCacheTransport(
        next_transport=AsyncHTTPTransport(),
        storage=storage_class(MemoryBlobStorage(), allow_heuristics=allow_heuristics),
        policy=SpecificationPolicy(
            cache_options=CacheOptions(shared=True, supported_methods=["GET", "HEAD"], allow_stale=False)
        ),
    )
    return AsyncClient(transport=transport, event_hooks=ENDPOINT_HOOKS)


def _origin(headers, *, revalidates=True):
    """An origin answering ``headers`` with a numbered body, or ``304`` to a request carrying a matching validator."""
    seen = []

    def respond(request):
        seen.append(request)
        validators = {request.headers.get("if-none-match"), request.headers.get("if-modified-since")} - {None}
        if revalidates and validators & {headers.get("etag"), headers.get("last-modified")}:
            return Response(304)
        return Response(200, content=f"body-{len(seen)}".encode(), headers=headers)

    respx.get(URL).mock(side_effect=respond)
    return seen


@pytest.mark.asyncio
class TestValidatorOnlyResponses:
    @respx.mock
    async def test_etag_is_revalidated_and_a_304_serves_the_stored_body(self):
        seen = _origin({"etag": '"v1"'})

        async with _client() as client:
            first = await client.get(URL)
            second = await client.get(URL)

        assert [r.headers.get("if-none-match") for r in seen] == [None, '"v1"']
        assert (first.content, second.content) == (b"body-1", b"body-1")

    @respx.mock
    async def test_last_modified_is_revalidated_and_a_304_serves_the_stored_body(self):
        last_modified = _http_date(timedelta(days=-30))
        seen = _origin({"last-modified": last_modified})

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)

        assert [r.headers.get("if-modified-since") for r in seen] == [None, last_modified]
        assert second.content == b"body-1"

    @respx.mock
    async def test_a_200_to_the_conditional_request_serves_the_new_body(self):
        seen = _origin({"etag": '"v1"'}, revalidates=False)

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)

        assert seen[1].headers.get("if-none-match") == '"v1"'
        assert second.content == b"body-2"

    @respx.mock
    async def test_the_entry_is_never_served_without_the_origin_confirming_it(self):
        """Every use asks the origin, whatever the age of the entry: a heuristic would have made later ones free."""
        seen = _origin({"last-modified": _http_date(timedelta(days=-365))})

        async with _client() as client:
            for _ in range(4):
                response = await client.get(URL)

        assert len(seen) == 4
        assert response.content == b"body-1"

    @respx.mock
    async def test_with_the_origin_down_the_request_fails(self):
        calls = []

        def respond(request):
            calls.append(request)
            if len(calls) > 1:
                raise httpx.ConnectError("down")
            return Response(200, content=b"body-1", headers={"etag": '"v1"'})

        respx.get(URL).mock(side_effect=respond)

        async with _client() as client:
            await client.get(URL)
            with pytest.raises(httpx.ConnectError):
                await client.get(URL)

    @respx.mock
    async def test_a_callers_response_is_not_handed_to_another_without_the_origin_confirming(self):
        """The credential is invisible to the cache key: the origin sees each caller's conditional request."""
        last_modified = _http_date(timedelta(days=-30))

        def respond(request):
            key = request.headers["x-api-key"]
            return Response(200, content=f"for-{key}".encode(), headers={"last-modified": last_modified})

        respx.get(URL).mock(side_effect=respond)

        async with _client() as client:
            await client.get(URL, headers={"x-api-key": "alice"})
            bob = await client.get(URL, headers={"x-api-key": "bob"})

        assert bob.content == b"for-bob"

    @respx.mock
    async def test_a_304_without_date_does_not_leak_the_marker_to_the_client(self):
        """The client sees the ``Date`` the origin gave the stored response, not the one that keeps it stale."""
        date = _http_date(timedelta(hours=-1))
        _origin({"etag": '"v1"', "date": date})

        async with _client() as client:
            await client.get(URL)
            second = await client.get(URL)
            third = await client.get(URL)

        assert second.headers["date"] == date
        assert third.headers["date"] == date
        assert "x-harp-original-date" not in third.headers

    @respx.mock
    async def test_the_marker_does_not_leak_when_the_stored_entry_cannot_be_refreshed(self):
        date = _http_date(timedelta(hours=-1))
        _origin({"etag": '"v1"', "date": date})

        async with _client(storage_class=_StorageThatCannotUpdate) as client:
            await client.get(URL)
            second = await client.get(URL)

        assert second.headers["date"] == date
        assert "x-harp-original-date" not in second.headers

    @respx.mock
    async def test_neither_validator_nor_expiry_is_not_retained(self):
        seen = _origin({})

        async with _client() as client:
            await client.get(URL)
            await client.get(URL)

        assert [r.headers.get("if-none-match") for r in seen] == [None, None]
        assert [r.headers.get("if-modified-since") for r in seen] == [None, None]

    @respx.mock
    async def test_no_cache_with_a_validator_is_not_retained(self):
        """hishel never reuses a ``no-cache`` entry, not even by revalidating it: keeping it would store for nothing."""
        _origin({"etag": '"v1"', "cache-control": "no-cache"})

        async with _client() as client:
            await client.get(URL)
            storage = client._transport.storage
            assert await storage.get_entries(await client._transport._key_for(httpx.URL(URL), "test-endpoint")) == []

    @respx.mock
    async def test_an_explicit_expiry_still_serves_without_asking(self):
        seen = _origin({"etag": '"v1"', "cache-control": "max-age=3600"})

        async with _client() as client:
            await client.get(URL)
            await client.get(URL)

        assert len(seen) == 1

    @respx.mock
    async def test_allow_heuristics_still_opts_into_heuristic_freshness(self):
        seen = _origin({"last-modified": _http_date(timedelta(days=-30))})

        async with _client(allow_heuristics=True) as client:
            await client.get(URL)
            await client.get(URL)

        assert len(seen) == 1
